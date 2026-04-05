# Ingress NGINX 退役了——你的遷移風險分析做了嗎？

> 2026 年 3 月 24 日，Kubernetes ingress-nginx 正式退役。影響約 50% 的 K8s 集群。ingress2gateway 幫你轉 YAML，但轉完之後呢？

## 問題不在格式轉換，在行為差異

Kubernetes 官方 blog（2026-02-27）記錄了 [5 個 surprising behaviors](https://kubernetes.io/blog/2026/02/27/ingress-nginx-before-you-migrate/)——這些差異會導致**靜默 404** 和路由失敗：

1. **Regex 行為不同**：ingress-nginx 是前綴匹配 + 大小寫不敏感，Gateway API 是全匹配 + 大小寫敏感
2. **use-regex 全域感染**：一個 Ingress 設了 use-regex，同 host 的所有 Ingress 路徑都變 regex
3. **rewrite-target 隱式啟用 regex**：完全沒文件記載的副作用
4. **結尾斜線自動 301**：Gateway API 不做
5. **URL 正規化差異**：`..` 和 `//` 的處理每個實作不同

**ingress2gateway 不偵測這些。Pluto 和 kubent 只看 apiVersion。**

## ShiftScope：遷移「之後」的風險分析

[ShiftScope](https://github.com/thc1006/shiftscope) 是一個 pluggable migration intelligence SDK。它不做格式轉換（ingress2gateway 做了），它做的是 ingress2gateway **不做的事**：

```bash
pip install shiftscope[cli]
shiftscope analyze gateway-api your-ingress.yaml --output markdown
```

輸出：
```
### [CRITICAL] use-regex applies globally: sibling Ingresses silently affected
- Ingress(es) ['api-ingress'] have use-regex=true on this host.
  This silently converts ALL paths on Ingress(es) ['web-ingress'] to regex mode.

### [CRITICAL] Snippet annotation(s) have NO Gateway API equivalent
- configuration-snippet cannot be portably represented in Gateway API.
```

## 不只是 Gateway API

ShiftScope 有 6 個 analyzer：

| Analyzer | 遷移路徑 |
|----------|----------|
| gateway-api | Ingress NGINX → Gateway API（9 behavioral + 9 annotation/TLS rules）|
| dra-network | Device Plugin → DRA |
| helm4-readiness | Helm 3 → Helm 4 |
| mcp-security | MCP server 安全掃描（OWASP ASI mapped）|
| agent-readiness | AI agent 生產就緒評估 |
| telco-intent | Telco YANG → GitOps |

## GitHub Action + SARIF

```yaml
- uses: thc1006/shiftscope/github-action@v0.4.0
  with:
    analyzer: gateway-api
    input-path: ./manifests/
    fail-on-critical: 'true'
    post-pr-comment: 'true'
```

每個 PR 自動分析，CRITICAL findings 直接擋 merge。SARIF 整合 GitHub Code Scanning。

## Container + Helm + MCP Server

v0.4.0 也支援容器化部署和 AI agent 整合：

```bash
# Docker
docker run ghcr.io/thc1006/shiftscope:0.4.0 analyze gateway-api /manifests/ingress.yaml

# Helm（一次性掃描）
helm install scan shiftscope/shiftscope --set job.inputPath=/manifests/ingress.yaml

# MCP Server（AI agent 消費）
shiftscope mcp-serve --http --host 127.0.0.1 --port 8080
```

## 試試看

```bash
pip install shiftscope[cli]
shiftscope list
shiftscope analyze gateway-api your-ingress.yaml --output table
```

PyPI: https://pypi.org/project/shiftscope/0.4.0/
GitHub: https://github.com/thc1006/shiftscope

---

*ShiftScope 是 Apache 2.0 開源專案。歡迎貢獻！*
