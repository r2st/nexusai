# =============================================================================
# Compute Module - Outputs
# =============================================================================

output "compute_id" {
  description = "Compute resource ID"
  value = var.cloud_provider == "azure" ? (
    var.deployment_type == "kubernetes" && length(azurerm_kubernetes_cluster.main) > 0 ?
    azurerm_kubernetes_cluster.main[0].id : null
  ) : var.cloud_provider == "aws" ? (
    var.deployment_type == "kubernetes" && length(aws_eks_cluster.main) > 0 ?
    aws_eks_cluster.main[0].id : null
  ) : var.cloud_provider == "gcp" ? (
    var.deployment_type == "kubernetes" && length(google_container_cluster.main) > 0 ?
    google_container_cluster.main[0].id : null
  ) : null
}

output "kubernetes_cluster_name" {
  description = "Kubernetes cluster name"
  value = var.cloud_provider == "azure" ? (
    var.deployment_type == "kubernetes" && length(azurerm_kubernetes_cluster.main) > 0 ?
    azurerm_kubernetes_cluster.main[0].name : null
  ) : var.cloud_provider == "aws" ? (
    var.deployment_type == "kubernetes" && length(aws_eks_cluster.main) > 0 ?
    aws_eks_cluster.main[0].name : null
  ) : var.cloud_provider == "gcp" ? (
    var.deployment_type == "kubernetes" && length(google_container_cluster.main) > 0 ?
    google_container_cluster.main[0].name : null
  ) : null
}

output "kubernetes_config" {
  description = "Kubernetes configuration for kubectl"
  value = var.cloud_provider == "azure" ? (
    var.deployment_type == "kubernetes" && length(azurerm_kubernetes_cluster.main) > 0 ?
    azurerm_kubernetes_cluster.main[0].kube_config_raw : null
  ) : null
  sensitive = true
}

output "kubernetes_host" {
  description = "Kubernetes API server host"
  value = var.cloud_provider == "azure" ? (
    var.deployment_type == "kubernetes" && length(azurerm_kubernetes_cluster.main) > 0 ?
    azurerm_kubernetes_cluster.main[0].kube_config[0].host : null
  ) : var.cloud_provider == "aws" ? (
    var.deployment_type == "kubernetes" && length(aws_eks_cluster.main) > 0 ?
    aws_eks_cluster.main[0].endpoint : null
  ) : var.cloud_provider == "gcp" ? (
    var.deployment_type == "kubernetes" && length(google_container_cluster.main) > 0 ?
    google_container_cluster.main[0].endpoint : null
  ) : null
}

output "bastion_public_ip" {
  description = "Bastion host public IP"
  value = var.cloud_provider == "azure" ? (
    length(azurerm_public_ip.bastion) > 0 ? azurerm_public_ip.bastion[0].ip_address : null
  ) : null
}
