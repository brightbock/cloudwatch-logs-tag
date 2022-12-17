import botocore
import boto3
import re
import os
import sys
import time
from datetime import datetime
from functools import cache, lru_cache


@cache
def refresh_regions(seed_region):
    regions = [seed_region]
    try:
        client = boto_client("ec2", seed_region)
        regions = [
            region["RegionName"]
            for region in client.describe_regions(
                AllRegions=True,
                Filters=[
                    {
                        "Name": "opt-in-status",
                        "Values": [
                            "opt-in-not-required",
                            "opted-in",
                        ],
                    },
                ],
            )["Regions"]
        ]
    except (
        botocore.exceptions.ClientError,
        botocore.exceptions.EndpointConnectionError,
    ) as e:
        print("ERROR: Refreshing region list from {} failed ({})".format(seed_region, e))
        pass
    return sorted(set(regions), key=lambda r: "###{}".format(r) if r in ["us-east-1"] else r)


def generate_lambda_arn(log_group_arn):
    arn_parts = log_group_arn.split(":")
    log_group_match = re.match(r"/aws/lambda/(us-east-1\.|)(.+)$", arn_parts[6])
    if not log_group_match:
        return ""
    lambda_region = arn_parts[3] if log_group_match.group(1) == "" else log_group_match.group(1).rstrip(".")
    lambda_name = log_group_match.group(2)
    lambda_arn = "{}:{}:{}:{}:{}:{}:{}".format(
        arn_parts[0],
        arn_parts[1],
        "lambda",
        lambda_region,
        arn_parts[4],
        "function",
        lambda_name,
    )
    return lambda_arn


@cache
def boto_client(service, region):
    return boto3.client(
        service,
        region_name=region,
        config=botocore_configuration,
    )


@lru_cache(maxsize=100000)
def get_tags_from_lambda(arn):
    region = arn.split(":")[3]
    tags = {}
    for attempt in range(1):
        try:
            client = boto_client("lambda", region)
            tags = client.list_tags(Resource=arn)["Tags"]
        except client.exceptions.TooManyRequestsException as e:
            print("WARNING: {}".format(e))
            time.sleep(5 * (attempt + 1))
            continue
        except client.exceptions.ResourceNotFoundException as e:
            break
    return tags


def get_tags_from_log_group(arn):
    region = arn.split(":")[3]
    log_group_name = arn.split(":")[6]
    tags = {}
    for attempt in range(1):
        try:
            client = boto_client("logs", region)
            tags = client.list_tags_for_resource(resourceArn=arn)["tags"]
        except client.exceptions.LimitExceededException as e:
            print("WARNING: {}".format(e))
            time.sleep(5 * (attempt + 1))
            continue
        except (client.exceptions.ResourceNotFoundException,) as e:
            print("WARNING: {}".format(e))
            break
    return tags


def lambda_handler(event, context):
    global last_execution_time
    global refresh_time
    global log_groups_done

    timestamp_now = int(datetime.now().timestamp())
    if (timestamp_now - last_execution_time) < 600:
        print("WARNING: Execution Throttled - Try again in 10 minutes")
        return
    last_execution_time = timestamp_now

    if (timestamp_now - refresh_time) > (86400 * 7):
        refresh_time = timestamp_now
        boto_client.cache_clear()
        refresh_regions.cache_clear()
        get_tags_from_lambda.cache_clear()
        log_groups_done = set()

    region_list = refresh_regions(SEED_REGION)

    for region_index, region in enumerate(region_list):

        print("==== [{:04d}/{:04d}] REGION: {}".format(region_index + 1, len(region_list), region))

        client = boto_client("logs", region)

        try:
            paginator = client.get_paginator("describe_log_groups")
            page_iterator = paginator.paginate(limit=10)

            for page in page_iterator:

                for log_group in page["logGroups"]:

                    log_group_name = log_group["logGroupName"]
                    log_group_arn = log_group["arn"].rstrip(":*")

                    lambda_arn = generate_lambda_arn(log_group_arn)

                    # Skip if this log group is not related to a lambda function, or has already been done
                    if (lambda_arn == "") or (log_group_arn in log_groups_done):
                        continue

                    log_groups_done.add(log_group_arn)

                    log_group_tags = get_tags_from_log_group(log_group_arn)

                    # Skip if log group already has required tags
                    tags_to_set = [tag for tag in PROPAGATE_TAG_NAMES if ((tag not in log_group_tags) or (log_group_tags[tag].strip() == ""))]
                    if len(tags_to_set) == 0:
                        continue

                    lambda_tags = get_tags_from_lambda(lambda_arn)

                    # Skip if lambda does not have any tag values to use
                    tag_dict_to_set = dict([(tag, lambda_tags[tag]) for tag in tags_to_set if ((tag in lambda_tags) and (lambda_tags[tag].strip() != ""))])
                    if len(tag_dict_to_set) == 0:
                        continue

                    print("== {} {} [{}] {}".format(region, "DRY_RUN" if DRY_RUN else "SET_TAG", log_group_name, str(tag_dict_to_set)))

                    if not DRY_RUN:
                        try:
                            client.tag_resource(resourceArn=log_group_arn, tags=tag_dict_to_set)
                        except (client.exceptions.ResourceNotFoundException,) as e:
                            print("WARNING: {}".format(e))

        except botocore.exceptions.ClientError as e:
            print("WARNING: {}".format(str(e)))
            # Next region
            continue
    print("INFO: {} -> {}".format("boto_client", boto_client.cache_info()))
    print("INFO: {} -> {}".format("regions", refresh_regions.cache_info()))
    print("INFO: {} -> {}".format("lambda_tags", get_tags_from_lambda.cache_info()))


SEED_REGION = os.getenv("SEED_REGION", "us-east-1")
DRY_RUN = str(os.getenv("DRY_RUN", "true")).strip().lower() not in ["no", "false", "0"]
PROPAGATE_TAG_NAMES = list(set([tag for tag in os.getenv("PROPAGATE_TAG_NAMES", "").split(",") if tag.strip() != ""]))

if len(PROPAGATE_TAG_NAMES) == 0:
    print("ERROR: Please set PROPAGATE_TAG_NAMES environment variable")
    sys.exit(1)

print("INFO: Tags to be propagated: {}".format(PROPAGATE_TAG_NAMES))

# Debug logging
# boto3.set_stream_logger(name='botocore')

botocore_configuration = botocore.config.Config(retries={"mode": "standard", "max_attempts": 2})
try:
    # Considering this makes multiple sequential calls to each region's CWL endpoint
    # enabling TCP keepalive is a good idea. However the version of botocore
    # included in Lambda/python3.9 runtime is currently 1.23.32, and `tcp_keepalive` is
    # from version 1.27.84. So try it, and recover gracefully on failure:
    botocore_configuration = botocore_configuration.merge(botocore.config.Config(tcp_keepalive=True))
except TypeError:
    print("INFO: Current botocore version does not support TCP keepalive")
    pass

last_execution_time = 0
refresh_time = 0
log_groups_done = set()

if __name__ == "__main__":
    context = []
    event = {}
    lambda_handler(event, context)
