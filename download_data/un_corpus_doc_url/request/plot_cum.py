import pandas as pd
import matplotlib.pyplot as plt

# 读取Excel文件
file_path = r'F:\联合国语料段落数分布.xlsx'  # 修改为你的文件路径
# file_path = r'F:\联合国语料token数分布.xlsx'  # 修改为你的文件路径
df = pd.read_excel(file_path)

# 查看数据结构，假设数据在第一个工作表中，列名分别是 'k' 和 'v'
print(df.head())

fkey = '文件数'
xkey = '段落数'
# xkey = 'token数'
ykey = 'Percentage'
# ykey = '段落数'

# 设置阈值过滤小值
threshold = 300  # 你可以根据需要调整这个阈值
total_files = df[fkey].sum()

filtered_df = df[df[fkey] > threshold]
filtered_df['Cumulative'] = filtered_df[fkey].cumsum()
# 将前缀和转换为占总文件数的百分比
filtered_df[ykey] = filtered_df['Cumulative'] / total_files * 100

# filtered_df = df
# filtered_df = df[df[ykey] < threshold]

x = filtered_df[xkey]
y = filtered_df[ykey]

# 绘制折线图
plt.plot(x, y, label='Percentage of Total Files by Paragraph Count')
# plt.plot(x, y, label='Percentage of Total Paragraphs by Token Count')

# 填充曲线下方区域
plt.fill_between(x, y, color='skyblue', alpha=0.4)

# plt.yscale('log')

# 添加标题和标签
plt.title('Cumulative Percentage of Files by Paragraph Count')
# plt.title('Cumulative Percentage of Paragraphs by Token Count')
plt.xlabel('Number of Paragraphs per File')
# plt.xlabel('Number of Token per Paragraph')
plt.ylabel('Percentage of Total Files (%)')
# plt.ylabel('Percentage of Total Paragraphs (%)')
plt.grid(True, which="both", ls="--")  # 调整网格线以适应对数尺度

# 添加图例
plt.legend()

plt.savefig(r'F:\para_cum.png', format='png', dpi=300)
# plt.savefig(r'F:\token_cum.png', format='png', dpi=300)
plt.show()
