# Food Delivery Microservices Platform on AWS EKS

A true microservices food delivery platform (Swiggy-style) deployed on a dedicated AWS EKS cluster, demonstrating service-to-service communication, path-based Ingress routing via AWS ALB, and infrastructure-as-code provisioning.

## Architecture
Internet
                        |
            AWS Application Load Balancer (ALB)
                (path-based Ingress routing)
                        |
    +-------------------+-------------------+-------------------+
    |                   |                   |                   |
`order-service` calls `user-service` and `restaurant-service` internally via Kubernetes DNS (`http://user-service:5000`) to validate users and fetch authoritative menu prices server-side — it never trusts client-submitted prices.

## Tech Stack

- **Compute:** AWS EKS (dedicated 2-node cluster, t3.small)
- **IaC:** Terraform (modular: provider, variables, data, iam, eks, outputs)
- **Containers:** Docker, 4 independently deployable services
- **Ingress:** AWS Load Balancer Controller (IRSA via OIDC, no static credentials)
- **Databases:** 3 isolated MySQL 8.0 instances (one per service — true microservices data isolation)
- **Local dev:** Docker Compose for full-stack local testing before cloud deployment

## Key Engineering Decisions

- **Service isolation:** Each microservice owns its own database; no shared schema or cross-service SQL queries
- **Server-side validation:** `order-service` independently verifies the user and re-fetches the menu item price from `restaurant-service` rather than trusting client input — preventing price tampering
- **IRSA over static credentials:** AWS Load Balancer Controller authenticates via IAM Roles for Service Accounts (OIDC), with zero AWS access keys stored in the cluster
- **Health check correctness:** Custom `/health` endpoints per service, wired into ALB target group health checks (default `/` path caused false-unhealthy target states)

## Real Issues Diagnosed and Resolved

1. **IAM policy version drift** — ALB Controller v3.4.0 required `elasticloadbalancing:DescribeListenerAttributes`, missing from the v2.7.2-era IAM policy; resolved by sourcing the policy from a matching controller release and pushing a new IAM policy version
2. **Subnet auto-discovery failure** — default VPC subnets lacked `kubernetes.io/role/elb` and `kubernetes.io/cluster/<name>` tags required for ALB Controller subnet discovery
3. **Security group deletion race condition** — ALB teardown intermittently hit `DependencyViolation` on security group deletion due to ENI detachment lag; resolved via controller's built-in retry
4. **Deprecated Ingress class annotation** — `kubernetes.io/ingress.class: alb` silently stopped being honored by the controller (which was explicitly configured with `--ingress-class=alb`); fixed by migrating to `spec.ingressClassName: alb`
5. **Unhandled database constraint violation** — `user-service` returned raw HTML 500 errors on duplicate email inserts instead of a structured JSON error; fixed with explicit `IntegrityError` handling and idempotent "existing user" response

## Local Development

```bash
docker-compose up -d --build
# Frontend:  http://localhost:8095
# user-service:        http://localhost:5001
# restaurant-service:  http://localhost:5002
# order-service:       http://localhost:5003
```

## Cloud Deployment

```bash
# 1. Provision EKS cluster
cd terraform
terraform init && terraform apply

# 2. Connect kubectl
aws eks update-kubeconfig --region ap-south-1 --name foodapp-eks-cluster

# 3. Install AWS Load Balancer Controller (IRSA + Helm)
eksctl utils associate-iam-oidc-provider --cluster foodapp-eks-cluster --approve
eksctl create iamserviceaccount --cluster foodapp-eks-cluster --namespace kube-system \
  --name aws-load-balancer-controller --attach-policy-arn <policy-arn> --approve
helm install aws-load-balancer-controller eks/aws-load-balancer-controller -n kube-system \
  --set clusterName=foodapp-eks-cluster --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

# 4. Deploy application
cd ../kubernetes
kubectl apply -f namespace.yaml -f secrets.yaml
kubectl apply -f user-mysql.yaml -f restaurant-mysql.yaml -f order-mysql.yaml
kubectl apply -f user-service.yaml -f restaurant-service.yaml -f order-service.yaml -f frontend.yaml
kubectl apply -f ingress.yaml

# 5. Get the public URL
kubectl get ingress -n foodapp
```

## Cleanup

```bash
cd terraform
terraform destroy
```
