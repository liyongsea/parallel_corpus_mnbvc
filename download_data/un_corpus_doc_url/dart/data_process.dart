import 'dart:io';

void main() {
  // 文件夹路径
  String folderPath = r'un_crawl_results';

  // 获取文件夹中的所有文件
  Directory folder = Directory(folderPath);
  List<FileSystemEntity> files = folder.listSync();

  final result = File('total_dataset.csv').openSync(mode: FileMode.append);
  // 遍历文件列表
  for (var file in files) {
    print(file.path.split('/').last);
    result.writeStringSync(File(file.path)
        .readAsLinesSync()
        .where((element) => element.contains(',DOC,'))
        .toList()
        .join('\n'));
    result.writeStringSync('\n');
  }
  print('成功！');
}
