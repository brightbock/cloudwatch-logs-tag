variable "project_name" {
  type    = string
  default = "cloudwatch_logs_tag_from_lambda"
}

variable "propagate_tag_names" {
  type = string
}

variable "schedule_expression" {
  type    = string
  default = "rate(23 hours)"
}

variable "seed_region" {
  type    = string
  default = ""
}

variable "dry_run" {
  type    = bool
  default = true
}

variable "lambda_log_retention_in_days" {
  type    = string
  default = "30"
}

#### THE DEFAULTS SHOULD BE FINE BELOW HERE ####

variable "lambda_src_dir" {
  type    = string
  default = ""
}

variable "lambda_layer_dir" {
  type    = string
  default = ""
}

variable "lambda_src_filename" {
  type    = string
  default = "lambda"
}

variable "lambda_zip_file" {
  type    = string
  default = ""
}

variable "lambda_memory_size" {
  type    = string
  default = "128"
}

variable "lambda_runtime" {
  type    = string
  default = "python3.10"
}

variable "lambda_architectures" {
  type    = set(string)
  default = ["arm64"]
}

variable "lambda_timeout" {
  type    = string
  default = "900"
}

