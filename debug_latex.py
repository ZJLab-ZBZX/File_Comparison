import argparse
import sys
from comparison_modules.latex_comparison.batch_compare import batch_compare


def main():
    # 创建简化的参数解析器
    parser = argparse.ArgumentParser(
        description='比较两个LaTeX文件',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # 添加两个必须的文件路径参数
    parser.add_argument(
        'file_path_1',
        type=str,
        help='第一个要比较的文件路径'
    )

    parser.add_argument(
        'file_path_2',
        type=str,
        help='第二个要比较的文件路径'
    )

    # 解析参数
    args = parser.parse_args()

    # 直接调用比较函数（不带任何额外参数）
    try:
        result = batch_compare(args.file_path_1, args.file_path_2)
        print(result)
    except Exception as e:
        print(f"处理失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()