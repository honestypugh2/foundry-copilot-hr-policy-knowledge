# ============================================================================
# HR Policy Knowledge Agent - Demo Infrastructure (Terraform)
# Variables
# ============================================================================

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "environment_name" {
  description = "Name of the environment (used as resource prefix suffix)"
  type        = string
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "eastus2"
}

variable "resource_prefix" {
  description = "Resource prefix for naming"
  type        = string
  default     = "hr-policy-kb"
}

variable "openai_deployment_name" {
  description = "Azure OpenAI chat model deployment name"
  type        = string
  default     = "gpt-4o"
}

variable "embedding_deployment_name" {
  description = "Azure OpenAI embedding model deployment name"
  type        = string
  default     = "text-embedding-3-small"
}

variable "search_sku" {
  description = "Azure AI Search SKU"
  type        = string
  default     = "basic"
  validation {
    condition     = contains(["basic", "standard"], var.search_sku)
    error_message = "search_sku must be 'basic' or 'standard'."
  }
}

variable "principal_id" {
  description = "Principal ID for RBAC role assignments (e.g. your user objectId)"
  type        = string
  default     = ""
}
