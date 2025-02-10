import boto3
import botocore
from botocore.exceptions import NoCredentialsError, ProfileNotFound

# Define the tags that should exist
REQUIRED_TAGS = {"Environment": "Production", "Owner": "CloudEng"}

# AWS services that support resource tagging
TAGGABLE_SERVICES = [
    "ec2", "s3", "rds", "lambda", "dynamodb", "sns", "sqs", "elb", "autoscaling",
    "cloudwatch", "redshift", "cloudfront", "eks", "ecr", "kinesis"
]

def get_aws_profiles():
    """Retrieve AWS profiles from the credentials file."""
    session = botocore.session.Session()
    return session.available_profiles

def get_resources_with_tags(client, service_name):
    """Retrieve all resources for a given AWS service that supports tagging."""
    try:
        tag_client = client.get_paginator("get_resources")
        resources = []
        
        for page in tag_client.paginate(ResourcesPerPage=50):
            resources.extend(page.get("ResourceTagMappingList", []))

        return resources
    except Exception as e:
        print(f"Error fetching resources for {service_name}: {e}")
        return []

def check_and_add_tags(client, resource_arn):
    """Check for missing tags on a resource and add them if necessary."""
    try:
        # Get existing tags
        existing_tags = {}
        tag_response = client.get_resources(ResourceARNList=[resource_arn])
        if "ResourceTagMappingList" in tag_response:
            for tag_mapping in tag_response["ResourceTagMappingList"]:
                for tag in tag_mapping.get("Tags", []):
                    existing_tags[tag["Key"]] = tag["Value"]

        # Identify missing tags
        missing_tags = [
            {"Key": key, "Value": value}
            for key, value in REQUIRED_TAGS.items()
            if key not in existing_tags
        ]

        # Add missing tags if any
        if missing_tags:
            client.tag_resources(ResourceARNList=[resource_arn], Tags={t["Key"]: t["Value"] for t in missing_tags})
            print(f"Added missing tags {missing_tags} to {resource_arn}")
        else:
            print(f"Resource {resource_arn} already has all required tags.")

    except Exception as e:
        print(f"Error processing resource {resource_arn}: {e}")

def process_aws_profile(profile_name):
    """Process each AWS profile and check tags across all taggable resources."""
    try:
        print(f"\nSwitching to profile: {profile_name}")
        session = boto3.Session(profile_name=profile_name)
        tag_client = session.client("resourcegroupstaggingapi")

        for service in TAGGABLE_SERVICES:
            print(f"Checking {service} resources...")
            resources = get_resources_with_tags(tag_client, service)
            for resource in resources:
                resource_arn = resource["ResourceARN"]
                check_and_add_tags(tag_client, resource_arn)

    except ProfileNotFound:
        print(f"Profile {profile_name} not found.")
    except NoCredentialsError:
        print(f"No credentials found for profile {profile_name}.")
    except Exception as e:
        print(f"Unexpected error on profile {profile_name}: {e}")

if __name__ == "__main__":
    profiles = get_aws_profiles()
    
    if not profiles:
        print("No AWS profiles found. Make sure you have configured them in ~/.aws/credentials.")
    else:
        for profile in profiles:
            process_aws_profile(profile)
