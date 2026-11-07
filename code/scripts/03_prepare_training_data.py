"""第 3 步：将四集合合并为 LLaMA-Factory ShareGPT 格式。"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from job_finetune_course.data_processing import export_llamafactory_dataset  # noqa: E402
from job_finetune_course.project_config import project_path  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir", default="code/data/datasets/candidates/gemini-v2-split-v2",
        help="第 2 步 --output-dir 指定的数据切分目录"
    )
    parser.add_argument("--output-dir", default="code/data/datasets/llamafactory")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    input_dir = project_path(args.input_dir)
    if not input_dir.is_dir():
        parser.error(
            f"输入目录不存在：{input_dir}。请用 --input-dir 指定第 2 步 --output-dir 的目录。"
        )

    report = export_llamafactory_dataset(
        input_dir,
        project_path(args.output_dir),
        overwrite=args.overwrite,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
