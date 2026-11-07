# Cloud Studio 云端运行

## 选择 Git 导入

本项目已有 Python 3.11、LLaMA-Factory 0.9.4、Qwen3 的 SFT/DPO 配置和正式语料，
优先通过 Git 导入，省去从模板建立空项目后再次迁移代码、数据和配置。
Git 负责传输版本化项目；GPU、驱动及依赖仍需在工作空间准备。
如果当前账户只能从 PyTorch/GPU 模板获得 GPU 环境，也可先创建该模板，再在终端 clone 本仓库，后续步骤相同。

腾讯云官方说明：
- [应用创建：模板、Git 导入和复刻](https://cloud.tencent.com/document/product/1039/131765)
- [模板中心：适用场景与 CPU/GPU 算力](https://cloud.tencent.com/document/product/1039/131796)

## 1. 导入项目

Cloud Studio → 创建应用 → 从 Git 仓库导入，填写本仓库地址，分支选择 `main`。
私有仓库需要工作空间拥有读取权限；如果网页不能直接导入私有仓库，
先创建 GPU 工作空间，再用该空间已授权的 Git 凭据 clone。
不要复制本机 SSH 私钥或把令牌写入仓库。

切换到提供 NVIDIA CUDA 的 GPU 算力后，在项目根目录先检查：

```bash
nvidia-smi
df -h .
```

当前 YAML 是 BF16 LoRA 配置。先用 4B 冒烟验证 CUDA 和训练链路，再尝试正式 8B；
能否训练取决于实际显存、驱动、上下文长度和 batch size。
基座、checkpoint、SFT/DPO 合并模型会占用多份模型空间，按实际工作量准备磁盘。

## 2. 恢复训练语料

```bash
bash code/scripts/10_restore_cloud_data.sh
```

`cloud-data/training-data.tar.gz` 保存当前完整的 `tasks_fixed` 和 LLaMA-Factory JSONL，
`cloud-data/SHA256SUMS` 校验归档完整性。解压不覆盖本地已有文件，重复执行会跳过旧文件。
`dataset_info.json` 直接由 Git 管理。
重复切分目录、原始 Excel、本机虚拟环境、已有训练输出和模型权重未上传。
已有正式训练数据可直接用于训练，无需重新切分。
若要教学演示切分，请指定新的输出目录。

## 3. 创建独立 Python 环境（仅在云端新克隆的项目执行）

项目本地使用共享 `.venv`，因此 `pyproject.toml` 设置了 `managed = false`。
新克隆的云端项目没有该环境，必须先开启 uv 管理，再安装；不要在原本机共享环境里执行以下修改。

先安装 uv（若镜像未提供，可按 [uv 官方安装说明](https://docs.astral.sh/uv/getting-started/installation/) 安装）。
然后在云端项目根目录执行：

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('pyproject.toml')
s = p.read_text(encoding='utf-8')
p.write_text(s.replace('managed = false', 'managed = true'), encoding='utf-8')
PY
uv sync --frozen --no-dev
uv run llamafactory-cli version
```

Python 版本由 `.python-version` 固定为 3.11，首次同步可能下载解释器和较大的 PyTorch/CUDA 依赖。
锁文件固定 Torch 2.11.0，镜像预装的 PyTorch 不保证与此版本相同；不要假设选择模板即可跳过安装。
`managed` 的云端修改无需提交；保持云端 `managed = true` 后运行下面的 `uv run`。

## 4. 下载模型到配置要求的位置

```bash
uv run python - <<'PY'
from modelscope import snapshot_download
snapshot_download('Qwen/Qwen3-4B', local_dir='model_files/Qwen3-4B')
# 正式训练 8B 时再执行：
# snapshot_download('Qwen/Qwen3-8B', local_dir='model_files/Qwen3-8B')
PY
uv run python code/scripts/00_check_env.py --model-path model_files/Qwen3-4B --require-cuda
```

模型在云端单独下载，不放入 Git。

## 5. 验证数据与训练

先运行无需加载模型的评测链路自检：

```bash
uv run python code/scripts/05_evaluate_model.py \
  --gold-as-prediction --limit 20 \
  --output-dir code/outputs/evaluation/cloud-pipeline-check
```

如需完整测试，安装开发依赖后执行：

```bash
uv sync --frozen
uv run python -m pytest code/tests -q
```

4B 冒烟和训练参数见 `doc/SFT_FULL_PIPELINE.md`，完整阶段与放行门禁见
`doc/FINETUNING_RUNBOOK.md`。8B 训练前继续按 `doc/QWEN3_8B_FINE_TUNING.md`
做 8B 独立环境、基座评测、SFT、DPO 和冻结集验收。

正式 SFT 命令（会启动训练）：

```bash
uv run llamafactory-cli train code/configs/qwen3_4b_sft.yaml
```

训练产物默认写入被 Git 忽略的 `code/outputs/`；需要另行备份，Git push 不会上传模型或 checkpoint。
