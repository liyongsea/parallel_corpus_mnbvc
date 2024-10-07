import pandas as pd
import matplotlib.pyplot as plt

# 读取Excel文件
# file_path = r'F:\联合国语料段落数分布.xlsx'  # 修改为你的文件路径
file_path = r'F:\联合国语料token数分布.xlsx'  # 修改为你的文件路径
df = pd.read_excel(file_path)

# 查看数据结构，假设数据在第一个工作表中，列名分别是 'k' 和 'v'
print(df.head())

# xkey = '段落数'
xkey = 'token数'
# ykey = '文件数'
ykey = '段落数'

# 设置阈值过滤小值
threshold = 10000  # 你可以根据需要调整这个阈值
filtered_df = df[df[ykey] > threshold]

print(len(filtered_df))

x = filtered_df[xkey]
y = filtered_df[ykey]

# 绘制折线图
# plt.plot(x, y, label='File Count vs Paragraph Count')
plt.plot(x, y, label='Paragraph Count vs Token Count')

# 填充曲线下方区域
plt.fill_between(x, y, color='skyblue', alpha=0.4)

# plt.yscale('log')

# 添加标题和标签
# plt.title('Distribution of Paragraphs per File Across Files')
plt.title('Distribution of Tokens per Paragraph Across Paragraphs')
# plt.xlabel('Number of Paragraphs per File')
plt.xlabel('Number of Tokens per Paragraph')
# plt.ylabel('Total Number of Files')
plt.ylabel('Total Number of Paragraphs')
plt.grid(True, which="both", ls="--")  # 调整网格线以适应对数尺度

# 添加图例
plt.legend()

# 绘制散点图
# plt.figure(figsize=(10, 6))
# plt.scatter(, , alpha=0.5)
# plt.title('filecount vs paracount')
# plt.xlabel('paracount')
# plt.ylabel('filecount')
# plt.grid(True)

# # 绘制直方图
# plt.figure(figsize=(10, 6))
# plt.hist(df['段落数'], weights=df['文件数'], bins=30, color='blue', alpha=0.7)
# plt.title('Weighted Distribution of 段落数')
# plt.xlabel('段落数')
# plt.ylabel('加权文件数')
# plt.grid(True)

# plt.figure(figsize=(10, 6))
# plt.hist(filtered_df['文件数'], bins=filtered_df['段落数'], color='blue', alpha=0.7)
# plt.title('Value Distribution Over Threshold')
# plt.xlabel('Value')
# plt.ylabel('Frequency')
# plt.grid(True)

# 保存图像，适合嵌入LaTeX
plt.savefig(r'F:\token_distri.png', format='png', dpi=300)
plt.show()
