import pandas as pd
import os
import argparse
from datetime import datetime
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.styles import Alignment, Font

def auto_adjust_column_width_and_font(ws: Worksheet):
    """
    自动调整列宽以适应内容，为指定列开启自动换行，并设置宋体12号字体
    """
    # 定义需要自动换行的列
    wrap_text_columns = ['J', 'K', 'L'] # 对应 '简述', '推荐理由', '预期'
    
    # 设置等线（正文）13号字体
    dengxian_font = Font(name='等线', size=13)

    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter  # 获取列字母
        
        # 遍历列中的所有单元格
        for cell in col:
            # 设置字体为等线（正文）13号
            cell.font = dengxian_font
            
            # 为指定列的单元格设置自动换行
            if column in wrap_text_columns:
                cell.alignment = Alignment(wrap_text=True, vertical='top')

            # 计算单元格内容的显示宽度
            try:
                cell_length = 0
                if cell.value:
                    for char in str(cell.value):
                        if '\u4e00' <= char <= '\u9fff': # 判断是否为中文字符
                            cell_length += 2
                        else:
                            cell_length += 1
                
                if cell_length > max_length:
                    max_length = cell_length
            except:
                pass
        
        # 对自动换行的列使用固定宽度，其他列自适应
        if column in wrap_text_columns:
            ws.column_dimensions[column].width = 45 # 为换行列设置一个较宽的固定值
        else:
            # 设置一个合理的最小和最大宽度
            adjusted_width = min(max(max_length + 2, 12), 60)
            ws.column_dimensions[column].width = adjusted_width

def convert_csv_to_excel(csv_path: str, excel_path: str):
    """
    将CSV文件转换为按日期分sheet的、格式优美的Excel文件，使用宋体12号字体
    """
    if not os.path.exists(csv_path):
        print(f"❌ 错误：找不到CSV文件 -> {csv_path}")
        return

    try:
        # 读取CSV文件，并解析日期
        df = pd.read_csv(csv_path)
        
        # 从文件名中提取基础日期
        base_date_str = os.path.basename(csv_path).replace('会议纪要_', '').replace('.csv', '')
        if base_date_str == 'result':
            base_date_str = datetime.now().strftime('%y.%m.%d')

        try:
            # 尝试从 YY.MM.DD 格式解析
            base_date = datetime.strptime(base_date_str, '%y.%m.%d')
        except ValueError:
            # 如果解析失败，则使用当天日期作为基准
            base_date = datetime.now()
            print(f"⚠️ 警告：无法从文件名解析日期，使用今天 ({base_date.strftime('%Y-%m-%d')}) 作为基准日期。")

        # 将'日期'列（HH:MM）和基础日期合并成完整的datetime对象
        # 注意：这里的'日期'列名是根据项目规范来的
        if '日期' in df.columns:
            df['full_date'] = df['日期'].apply(lambda x: base_date.strftime('%Y-%m-%d') + ' ' + str(x))
            df['full_date'] = pd.to_datetime(df['full_date'], format='%Y-%m-%d %H:%M', errors='coerce')
            df['date_only'] = df['full_date'].dt.date
        else:
            print("❌ 错误：CSV文件中缺少'日期'列，无法按日期分表。")
            return
        
        # 按日期分组
        grouped = df.groupby('date_only')
        
        # 创建Excel写入器
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # 遍历每个日期的分组
            for date_group, data in grouped:
                sheet_name = date_group.strftime('%Y-%m-%d')
                
                # 移除用于分组的辅助列
                data_to_write = data.drop(columns=['full_date', 'date_only'])
                
                # 写入到对应的sheet
                data_to_write.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 获取worksheet对象并调整列宽和字体
                worksheet = writer.sheets[sheet_name]
                auto_adjust_column_width_and_font(worksheet)

        print(f"✅ 成功！已将 {csv_path} 转换为 {excel_path}")
        print("   - 每个日期的数据已存入独立的Sheet（工作表）。")
        print("   - 所有文本已设置为宋体12号字体。")
        print("   - 所有列已自动调整宽度以舒适阅读。")

    except Exception as e:
        print(f"❌ 转换过程中发生错误: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CSV to Excel 转换器，带自动格式化功能。")
    parser.add_argument(
        '--input',
        type=str,
        default='output/result.csv',
        help='输入的CSV文件路径 (默认: output/result.csv)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='输出的Excel文件路径 (默认: 与输入文件同名，扩展名为.xlsx)'
    )
    
    args = parser.parse_args()

    # 如果未指定输出路径，则根据输入路径自动生成
    output_path = args.output
    if output_path is None:
        # 将.csv扩展名替换为.xlsx
        base_name = os.path.splitext(args.input)[0]
        output_path = f"{base_name}.xlsx"

    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    convert_csv_to_excel(args.input, output_path) 