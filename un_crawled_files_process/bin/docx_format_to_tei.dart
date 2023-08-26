import 'dart:io';

///将docx文件批量转换为tei文件
///使用pandoc的命令行命令来处理，请确保将它的安装目录添加到环境变量了
void main(List<String> args) {
  //这是目标文件夹，是待处理的文件夹，需要修改
  final targetDirectory = Directory(r'docx_format');

  //这是结果文件夹，放置处理好后的文件，会依照原来的文件夹结构, 按需修改
  final resultDirectory = Directory(r'tei_format');

  var processProgress = 1;
  final targetFileNumber = targetDirectory.listSync().length;
  //遍历目标文件夹下的每个文件夹
  for (var directory
      in targetDirectory.listSync().map((e) => Directory(e.path))) {
    print('正在处理($processProgress/$targetFileNumber):${directory.path}');

    final directoryPath = directory.path;

    Directory(
            '${resultDirectory.path}${directoryPath.replaceAll(directory.parent.path, '')}')
        .createSync(recursive: true);
    //这里是windows下运行，如果是linux或者其他系统，需要改exe后缀
    for (var file in directory.listSync()) {
      final a = Process.runSync(
          'pandoc.exe',
          [
            '${file.path}',
            '-o',
            '${resultDirectory.path}${file.path.replaceAll(file.parent.parent.path, '').replaceAll('.docx', '.tei')}'
          ],
          runInShell: true);
    }

    processProgress++;
  }
}
