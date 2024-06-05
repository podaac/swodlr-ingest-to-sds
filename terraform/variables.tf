variable "app_name" {
    default = "swodlr"
    type = string
}

variable "service_name" {
    default = "ingest-to-sds"
    type = string
}

variable "default_tags" {
    type = map(string)
    default = {}
}

variable "stage" {
    type = string
}

variable "region" {
    type = string
}

variable "sds_pcm_release_tag" {
    type = string
    default = null
}

variable "sds_host" {
    type = string
    sensitive = true
}

variable "sds_username" {
    type = string
    sensitive = true
}

variable "sds_password" {
    type = string
    sensitive = true
}

variable "sds_ca_cert_path" {
    type = string
    default = "/etc/ssl/certs/JPLICA.Root.pem"
}
