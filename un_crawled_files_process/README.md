使用方法：
1：安装好dart语言。

2：新建空白word，添加vba宏，将里面的文件夹路径改为实际的待处理的路径，然后运行，他会自动递归的将doc转为docx，中途中断了也没关系， 他会只处理doc文件，不会重头来。

3：使用指令 `dart docx_format_to_tei.dart` 将docx格式文件批量转换为tei格式，需要安装pandoc，并添加到环境变量。

代码都是在windows上测试的，linux上可能涉及文件路径的'\'和'/'的区别。
