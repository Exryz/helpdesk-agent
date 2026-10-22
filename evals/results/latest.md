# Helpdesk Agent Evaluation Report

- **Timestamp:** `20261021_172433`
- **Execution Mode:** `Production (live models)`

## Retrieval Performance Comparison

| Retrieval Mode | Hit@1 | Hit@3 | Hit@4 | MRR | Recall@4 | Evaluated Rows |
|---|---|---|---|---|---|---|
| `bm25` | 94.6% | 100.0% | 100.0% | 0.9685 | 100.0% | 37 |
| `dense` | 97.3% | 100.0% | 100.0% | 0.9820 | 100.0% | 37 |
| `hybrid` | 94.6% | 100.0% | 100.0% | 0.9730 | 100.0% | 37 |
| `hybrid_rerank` | 94.6% | 97.3% | 100.0% | 0.9662 | 100.0% | 37 |

### Breakdown by Category

| Retrieval Mode | Category | Count | Hit@1 | Hit@4 | MRR | Recall@4 |
|---|---|---|---|---|---|---|
| `bm25` | kb_answer | 35 | 94.3% | 100.0% | 0.9667 | 100.0% |
| `bm25` | ticket_action | 2 | 100.0% | 100.0% | 1.0000 | 100.0% |
| `dense` | kb_answer | 35 | 97.1% | 100.0% | 0.9810 | 100.0% |
| `dense` | ticket_action | 2 | 100.0% | 100.0% | 1.0000 | 100.0% |
| `hybrid` | kb_answer | 35 | 94.3% | 100.0% | 0.9714 | 100.0% |
| `hybrid` | ticket_action | 2 | 100.0% | 100.0% | 1.0000 | 100.0% |
| `hybrid_rerank` | kb_answer | 35 | 94.3% | 100.0% | 0.9643 | 100.0% |
| `hybrid_rerank` | ticket_action | 2 | 100.0% | 100.0% | 1.0000 | 100.0% |
