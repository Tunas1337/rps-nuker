# rps-nuker.py
# Author: Andrej A <tunas@cryptolab.net>
# Date: 2026-03-06
# This script is used to delete devices en masse from the Yealink RPS server.

# Usage Example:
# echo -e "805ec0ad818c\n805ec0ad818d\n805ec0ad818e\nend" | ./rps-nuker.py --token "<token>"
# This will delete the devices with the MAC addresses 805ec0ad818c, 805ec0ad818d, and 805ec0ad818e.
# The script will prompt you to confirm before proceeding with the deletions.

import sys
import argparse
import requests
import json

global token
token = "FOO-BAR-BAZ" # either hard-coded or passed as an argument


def parse_args():
    parser = argparse.ArgumentParser(
        description="Delete Yealink RPS devices by list of MAC addresses (read from stdin)."
    )
    parser.add_argument(
        "--token",
        dest="token",
        help="WEBYIOTMANAGER cookie value. If omitted, uses the hard-coded default.",
    )
    return parser.parse_args()

# Function to read newline-separated MAC addresses from stdin
def get_macs_from_stdin():
    macs = set()
    for line in sys.stdin:
        if line.startswith('#'):
            continue
        if line.startswith("end"):
            break
        mac = ''.join(filter(str.isalnum, line.strip())).upper()
        if mac:
            macs.add(mac)
    return list(macs)

# Get the device id for a single MAC by sending a pagedList request
def get_device_id_for_mac(mac):
    url = "https://us.ymcs.yealink.com/manager/rps-manager/api/v1/manager/rps/device/pagedList"
    payload = {
        "status": None,
        "searchKey": mac,
        "skip": 0,
        "limit": 1,
        "orderbys": [],
        "autoCount": True
    }
    try:
        # add cookie
        cookies = {
            "WEBYIOTMANAGER": token
        }
        r = requests.post(url, json=payload, cookies=cookies)
        r.raise_for_status()
      #  print(f"Response: {r.text}")
        data = r.json()
        items = data.get("data", {}).get("data", [])
        if items:
            return items[0]["id"]
        else:
            print(f"No device found for MAC {mac}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Error querying ID for MAC {mac}: {e}", file=sys.stderr)
        return None

# Look up all device ids for the list of macs
def get_device_ids_for_macs(macs):
    ids = []
    for mac in macs:
        id = get_device_id_for_mac(mac)
        if id is not None:
            ids.append(id)
    return ids

def batch_delete_device_ids(ids):
    if not ids:
        print("No IDs to delete.")
        return
    url = "https://us.ymcs.yealink.com/manager/rps-manager/api/v1/manager/rps/device/batchDelete"
    cookies = {
        "WEBYIOTMANAGER": token
    }
    success = 0
    failed = 0
    for device_id in ids:
        payload = {"ids": [device_id]}
        try:
            print(f"Deleting device ID: {device_id}")
            r = requests.post(url, json=payload, cookies=cookies)
            r.raise_for_status()
#            print("Delete response:", r.text)
            success += 1
        except Exception as e:
            print(f"Delete failed for ID {device_id}: {e}", file=sys.stderr)
            failed += 1
    print(f"Deletion complete. Succeeded: {success}, Failed: {failed}")


if __name__ == "__main__":
    args = parse_args()
    if args.token:
        token = args.token
    macs = get_macs_from_stdin()
    if not macs:
        print("No MACs supplied.")
        sys.exit(1)
    # Confirm before proceeding with deletions
    print(f"Collected {len(macs)} MAC address(es):")
    for mac in macs:
        print(f"  {mac}")
    try:
        confirm = input("Type 'yes' to proceed with deletion, or anything else to cancel: ").strip().lower()
    except EOFError:
        print("No confirmation received. Aborting without deleting.")
        sys.exit(1)
    if confirm not in ("yes", "y"):
        print("Deletion cancelled.")
        sys.exit(0)
    device_ids = get_device_ids_for_macs(macs)
    if not device_ids:
        print("No device IDs found for the supplied MACs.")
        sys.exit(1)
    batch_delete_device_ids(device_ids)