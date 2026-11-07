# 数据目录说明

本目录用于存放微调所需的语料与数据集。为控制仓库体积，**真实训练数据与模型权重未随代码一并复制**，此处仅保留数据集注册表 `datasets/llamafactory/dataset_info.json`（供 LLaMA-Factory 识别数据集名称与格式）。

## 目录约定

```text
code/data/
└── datasets/
    └── llamafactory/
        ├── dataset_info.json                       # 数据集注册表（已保留）
        ├── recruitment_sft_train.jsonl             # SFT 训练集（需自行准备）
        ├── recruitment_sft_dev.jsonl               # SFT 验证集（需自行准备）
        ├── recruitment_sft_diagnostic.jsonl        # 调试集（需自行准备）
        ├── recruitment_sft_frozen_test.jsonl       # 冻结测试集（需自行准备）
        ├── recruitment_dpo_codex_direct_v2_train.jsonl   # DPO 训练集（需自行准备）
        └── recruitment_dpo_codex_direct_v2_eval.json     # DPO 偏好评测集（需自行准备）
```

## 数据来源与准备

* 原始微调语料、SFT/DPO 数据集的生成与质检流程，见 `doc/CORPUS_PREPARATION.md` 与 `doc/DPO_DATA_DESIGN_PLAN.md`。
* 数据集如何注册到 `dataset_info.json`、各字段含义，见教案「⑤ 模型微调」对应小节。
* 基座模型 `Qwen3-4B` / `Qwen3-8B` 需另行下载到项目根目录的 `model_files/` 下（配置中 `model_name_or_path` 指向它）。

> 本课程的代码讲解不依赖真实数据即可读懂；若要实际跑通训练，请按上述文档补齐数据与模型。
