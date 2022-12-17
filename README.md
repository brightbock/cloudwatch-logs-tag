![GitHub](https://img.shields.io/github/license/brightbock/cloudwatch-logs-tag) ![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/brightbock/cloudwatch-logs-tag) ![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/brightbock/cloudwatch-logs-tag/terraform.yml?branch=main)

#  CloudWatch Logs Log Group Tagging

_TLDR: This propagates specified tags from the Lambda function that generated the logs to the CloudWatch Logs log group where the logs are stored._

Logs from Lambda functions are stored in CloudWatch Logs by default. If a CloudWatch Logs log group does not exist already, one will be created automatically the first time a function executes (if the function execution role has permission).

Lambda functions may have been meticulously tagged during deployment for cost allocation or attribute-based access control (ABAC) purposes. This Terraform module / AWS [Lambda function](https://github.com/brightbock/cloudwatch-logs-tag/blob/main/src/lambda.py) will ensure each function's CloudWatch Logs log group is correspondingly tagged.

All log groups with names beginning with `/aws/lambda/` will be checked to ensure the tags named in the `propagate_tag_names` comma-spearated list exist. If the tags exist and have values set then no action is taken - _Tags are only added or updated if they don't already exist_, or if the current tag value is empty or only whitespace. Missing tags will be added to the log group if the corresponding Lambda function has a tag of the same name.

This will determine the regions accessible in your account automatically and process all of them (you do not need to deploy this to each region separately).

Tagging will be automatically triggered according to the `schedule_expression` [schedule expression](https://docs.aws.amazon.com/lambda/latest/dg/services-cloudwatchevents-expressions.html). The default is to trigger approximately every 23 hours.

You can deploy with `dry_run = "true"` to see what will happen without actually changing any log group tags.

## How to use:

1. Add a module definition to your Terraform. See the example below.
2. Update the module configuration to match your requirements, and apply your Terraform.
3. Open the CloudWatch Log log group for this Lambda function to see what it did.

```
module "cloudwatch_logs_tag" {
  source                = "git::https://github.com/brightbock/cloudwatch-logs-tag.git?ref=v0.1.0"
  project_name          = "cloudwatch_logs_tag_from_lambda"
  propagate_tag_names   = "team,project"
  dry_run               = "false"
  # schedule_expression   = "rate(23 hours)"
  # providers             = { aws = aws.use1 }
}
```

