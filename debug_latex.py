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
        default='/data/西子数据/CPS1000',
        help='要处理的目录路径'
    )

    # 添加布尔类型参数1（默认True，可通过命令行设为False）
    parser.add_argument(
        '--disable-feature1',  # 注意名称改为"disable"
        dest='enable_feature1',  # 但目标变量名保持为enable_feature1
        action='store_false',  # 当提供参数时存储False
        default=True,  # 默认值为True
        help='禁用功能1（默认启用）'
    )

    # 添加布尔类型参数2（默认True，可通过命令行设为False）
    parser.add_argument(
        '--disable-feature2',
        dest='enable_feature2',
        action='store_false',
        default=True,
        help='禁用功能2（默认启用）'
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