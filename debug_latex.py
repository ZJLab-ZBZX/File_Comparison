import argparse
import sys
from comparison_modules.latex_comparison.batch_compare import batch_compare


def main():
    # 创建参数解析器
    parser = argparse.ArgumentParser(
        description='批量比较LaTeX文件',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # 添加路径参数（位置参数）
    parser.add_argument(
        'directory_path',
        type=str,
        default='/data/西子数据/CPS1000',  # 默认值
        help='要处理的目录路径'
    )

    # 添加布尔类型参数1
    parser.add_argument(
        '--enable-feature1',
        action='store_true',  # 当提供该参数时值变为True，否则为False
        default=True,
        help='启用功能1'
    )

    # 添加布尔类型参数2
    parser.add_argument(
        '--enable-feature2',
        action='store_true',
        default=True,
        help='启用功能2'
    )

    # 解析参数
    args = parser.parse_args()

    # 调用批量比较函数，传递参数
    try:
        result = batch_compare(
            directory_path=args.directory_path,
            enable_feature1=args.enable_feature1,
            enable_feature2=args.enable_feature2
        )
        print(result)
    except Exception as e:
        print(f"处理失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()