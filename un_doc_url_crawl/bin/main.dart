import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:puppeteer/puppeteer.dart';
import 'package:html/parser.dart' as html_paser;

var browser;

var page1;
void main(List<String> args) async {
  browser = await puppeteer.launch(headless: false);
  page1 = await browser.newPage();

  final random = Random();
  final directory = Directory('un_crawl_results');
  if (!directory.existsSync()) {
    directory.createSync();
  }

  //日期表
  final String datesPath;
  //起始点
  final int startPoint;
  //结束点
  int endPoint;
  if (args.length == 3) {
    datesPath = args[0];
    startPoint = int.parse(args[1]);
    endPoint = int.parse(args[2]);
  } else {
    print('例子：un_crawl dates.txt 0 -1');
    exit(0);
  }

  if (startPoint > endPoint) {
    print('起始点大于结束点');
    exit(1);
  }

  final dateList = jsonDecode(File(datesPath).readAsStringSync());
  if (endPoint == -1) {
    endPoint = dateList.length;
  }
  if ((startPoint > dateList.length) || (endPoint > dateList.length)) {
    print('起始点或结束点大于日期表');
    exit(1);
  }

  //开始循环获取
  for (var i = startPoint; i < endPoint + 1; i++) {
    await page1.goto('https://documents.un.org/prod/ods.nsf/home.xsp',
        timeout: Duration(days: 9999));
    //随机延迟5到10秒，防止过快
    sleep(Duration(seconds: random.nextInt(5) + 5));

    print('进度：$i /$endPoint');
    await getUrls(dateList: dateList, targetPoint: i);
  }

  print('完成！');
}

Future<List> getUrls(
    {required List<dynamic> dateList, required int targetPoint}) async {
  final dateFrom = dateList[targetPoint][0];
  final dateTo = dateList[targetPoint][1];

  final resultList = [];

  //搜索指定日期的文件，例如：03/08/2023
  await page1.$eval(
      '#widget_view\\:_id1\\:_id2\\:dtRelDateFrom > div.dijitReset.dijitInputField.dijitInputContainer > input[type=hidden]:nth-child(2)',
      '(node)=>node.value = "$dateFrom"');
  await page1.$eval(
      '#widget_view\\:_id1\\:_id2\\:dtRelDateTo > div.dijitReset.dijitInputField.dijitInputContainer > input[type=hidden]:nth-child(2)',
      '(node)=>node.value = "$dateTo"');
  await page1.clickAndWaitForNavigation('#view\\:_id1\\:_id2\\:btnRefine',
      timeout: Duration(days: 9999));

  while (true) {
    //获取当前页的所有目标链接
    final document =
        html_paser.parse(await page1.$eval('html', '(node)=>node.outerHTML'));
    //所有文件
    final allFiles = document.querySelectorAll(
        '#view\\:_id1\\:_id2\\:cbMain\\:_id136\\:rptResults > div');
    //每个文件单独处理
    for (var file in allFiles) {
      //文号
      final id = file.querySelector(".odsText.pull-right.flip")!.text;
      //所有语言版本
      final allLanguages =
          file.querySelectorAll('.details div.row.noMargin > div');

      for (var language in allLanguages) {
        final pdf = language.querySelectorAll('div')[3].querySelector('a');
        if (pdf != null) {
          var temp =
              '${dateFrom}_$dateTo,$id,${pdf.attributes['title']!.replaceAll(' ', '').replaceFirst('打开', '').replaceFirst('PDF文件', ',PDF')},${pdf.attributes['href']!.replaceFirst('?OpenElement', '')}';

          resultList.add(temp);
        }

        final doc = language.querySelectorAll('div')[4].querySelector('a');

        if (doc != null) {
          var temp =
              '${dateFrom}_$dateTo,$id,${doc.attributes['title']!.replaceAll(' ', '').replaceFirst('打开', '').replaceFirst('DOC文件', ',DOC').replaceFirst('Word文件', ',DOC')},${doc.attributes['href']!.replaceFirst('?OpenElement', '')}';

          resultList.add(temp);
        }
      }
    }

    //判断当前页是否是最后一页
    final finalNumber = int.parse(await page1.$eval(
        '#view\\:_id1\\:_id2\\:cbMain\\:_id136\\:cfPageTitle > b:nth-child(4)',
        '(node)=>node.textContent'));

    final totalNumber = int.parse(await page1.$eval(
        '#view\\:_id1\\:_id2\\:cbMain\\:_id136\\:cfPageTitle > b:nth-child(2)',
        '(node)=>node.textContent'));

    if (finalNumber == totalNumber) {
      print('最后一页($finalNumber/$totalNumber)');
      break;
    } else {
      print('不是最后一页($finalNumber/$totalNumber)');

      //判断点击下一页并判断是否已经到下一页，别问为啥不用clickAndWaitForNavigation()。
      await page1.$eval(
          '#view\\:_id1\\:_id2\\:cbMain\\:_id136\\:pager1__Next__lnk',
          '(node)=>node.click()');
      var detectedTimes = 0;
      while (true) {
        sleep(Duration(seconds: 1));
        final document = html_paser
            .parse(await page1.$eval('html', '(node)=>node.outerHTML'));
        final finalNumberNow = int.parse(await page1.$eval(
            '#view\\:_id1\\:_id2\\:cbMain\\:_id136\\:cfPageTitle > b:nth-child(4)',
            '(node)=>node.textContent'));
        if (finalNumberNow != finalNumber) {
          print('跳转成功($finalNumberNow/$totalNumber)');
          break;
        } else {
          print('等待跳转($detectedTimes秒)......($finalNumberNow/$totalNumber)');
          detectedTimes++;
        }
      }
    }
  }
  //储存文件

  final saveFile = File(
      './un_crawl_results/saveFile_${targetPoint}_${dateList.length - 1}.txt');
  saveFile.writeAsStringSync(resultList.join('\n'));
  print(resultList.join('\n'));

  return resultList;
}
