"""Retry a single Snoopy A1 launch when OCI reports no host capacity."""

import datetime
import os
import time

import oci
import requests


INSTANCE_NAME = "snoopy-a1"
ARM_OCPUS = 1
ARM_MEMORY_IN_GBS = 6
BOOT_VOLUME_SIZE_IN_GBS = 50
RETRY_INTERVAL = 300


def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required GitHub Actions secret: {name}")
    return value


def main():
    compartment_id = required("OCI_COMPARTMENT_ID")
    subnet_id = required("OCI_SUBNET_ID")
    ssh_public_key = required("A1_SSH_PUBLIC_KEY")
    if not ssh_public_key.startswith(("ssh-rsa ", "ssh-ed25519 ", "ecdsa-sha2-")):
        raise ValueError("A1_SSH_PUBLIC_KEY must contain a public SSH key, not a private key")

    config = oci.config.from_file()
    oci.config.validate_config(config)
    identity = oci.identity.IdentityClient(config)
    compute = oci.core.ComputeClient(config)
    network = oci.core.VirtualNetworkClient(config)

    subnet = network.get_subnet(subnet_id).data
    if subnet.compartment_id != compartment_id:
        raise ValueError("OCI_SUBNET_ID must be in OCI_COMPARTMENT_ID")
    if subnet.prohibit_public_ip_on_vnic:
        raise ValueError("OCI_SUBNET_ID must allow public IP addresses")

    domains = identity.list_availability_domains(compartment_id).data
    if not domains:
        raise RuntimeError("No availability domain found in this region")
    ad_name = domains[0].name

    images = compute.list_images(
        compartment_id,
        operating_system="Canonical Ubuntu",
        operating_system_version="22.04",
        shape="VM.Standard.A1.Flex",
        sort_by="TIMECREATED",
        sort_order="DESC",
    ).data
    if not images:
        raise RuntimeError("No compatible Ubuntu 22.04 Arm image found")
    image_id = images[0].id

    def find_existing():
        instances = oci.pagination.list_call_get_all_results(
            compute.list_instances, compartment_id, display_name=INSTANCE_NAME
        ).data
        return next(
            (
                instance for instance in instances
                if instance.display_name == INSTANCE_NAME
                and instance.shape == "VM.Standard.A1.Flex"
                and instance.lifecycle_state not in ("TERMINATED", "TERMINATING")
            ),
            None,
        )

    attempt = 0
    while True:
        existing = find_existing()
        if existing:
            print(f"A1 already exists ({existing.lifecycle_state}): {existing.id}")
            return

        attempt += 1
        now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        print(f"[{now}] Attempt #{attempt} to launch {INSTANCE_NAME}", flush=True)
        try:
            instance = compute.launch_instance(
                oci.core.models.LaunchInstanceDetails(
                    compartment_id=compartment_id,
                    display_name=INSTANCE_NAME,
                    availability_domain=ad_name,
                    shape="VM.Standard.A1.Flex",
                    shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                        ocpus=ARM_OCPUS, memory_in_gbs=ARM_MEMORY_IN_GBS
                    ),
                    source_details=oci.core.models.InstanceSourceViaImageDetails(
                        image_id=image_id,
                        boot_volume_size_in_gbs=BOOT_VOLUME_SIZE_IN_GBS,
                    ),
                    create_vnic_details=oci.core.models.CreateVnicDetails(
                        subnet_id=subnet_id, assign_public_ip=True
                    ),
                    metadata={"ssh_authorized_keys": ssh_public_key},
                )
            ).data
            print(f"Created A1 ({instance.lifecycle_state}): {instance.id}", flush=True)
            return
        except oci.exceptions.ServiceError as exc:
            message = (exc.message or "").lower()
            if exc.code == "OutOfHostCapacity" or "out of host capacity" in message:
                print("Out of host capacity; trying again later", flush=True)
            else:
                raise
        except requests.exceptions.RequestException as exc:
            print(f"Temporary connection error ({type(exc).__name__}); checking again later", flush=True)
        time.sleep(RETRY_INTERVAL)


if __name__ == "__main__":
    main()
