import 'dart:convert';
import 'dart:io';

void main(List<String> args) {
  //获取2000-01-01到2023-08-01的日期字符串每星期一个区间
  DateTime startDate = DateTime(2000, 1, 1);
  DateTime endDate = DateTime(2023, 8, 10);
  if (args.length >= 2) {
    String startDateString = args[0];
    String endDateString = args[1];

    try {
      startDate = DateTime.parse(startDateString);
      endDate = DateTime.parse(endDateString);
    } catch (e) {
      print("参数错误，例子:get_date_range 2000-01-01 2023-08-01");
    }
  } else {
    print("参数多或少了，例子:get_date_range 2000-01-01 2023-08-01");
  }

  List<DateTime> dates = [];
  for (DateTime date = startDate;
      date.isBefore(endDate);
      date = date.add(Duration(days: 1))) {
    dates.add(date);
  }
  List<String> dateStrings =
      dates.map((date) => date.toString().split(' ')[0]).toList();
  final dateEveryWeeks = dateStrings
      .asMap()
      .entries
      .where((e) {
        return (e.key % 7 == 0) || ((e.key + 1) % 7 == 0);
      })
      .map((e) => e.value)
      .toList();

  final dateFromList = [];
  final dateToList = [];
  for (var i = 0; i < dateEveryWeeks.length; i++) {
    if (i % 2 == 0) {
      dateFromList.add(dateEveryWeeks[i]);
    } else {
      dateToList.add(dateEveryWeeks[i]);
    }
  }

  print('dateFromList(${dateFromList.length}):$dateFromList');
  print('dateToList(${dateFromList.length}):$dateToList');

  final file = File('dates.txt');

  final resultList = [];
  for (var i = 0;
      i <
          ((dateToList.length < dateFromList.length)
              ? dateToList.length
              : dateFromList.length);
      i++) {
    resultList.add([dateFromList[i], dateToList[i]]);
  }
  final resultListJson = jsonEncode(resultList);
  print(resultListJson);
  file.writeAsStringSync(resultListJson);
}
