#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <unordered_set>
#include <set>
#include <map>
#include <unordered_map>
#include <sstream>
#include <algorithm>
#include <filesystem>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <chrono>
#include <cctype>
#include <iterator>
#include <optional>

#include "json.hpp" // 请确保nlohmann/json已在此路径可用
#include "md5.h"    // 引用stbrumme/hash-library
// Windows 编译命令: cl /std:c++20 /O2 jsonl_chk.cpp md5.cpp
// Windows cmd 使用 jsonl_chk.exe 之前需要先chcp 65001
using json = nlohmann::json;
namespace fs = std::filesystem;

// 全局模拟Python的逻辑
static bool is_first = true;

static std::vector<std::string> KEEP_KEYS = {
    "行号",
    "是否重复",
    "是否跨文件重复",
    "it_text",
    "zh_text",
    "en_text",
    "ar_text",
    "nl_text",
    "de_text",
    "eo_text",
    "fr_text",
    "he_text",
    "ja_text",
    "pt_text",
    "ru_text",
    "es_text",
    "sv_text",
    "ko_text",
    "th_text",
    "id_text",
    "cht_text",
    "vi_text",
    "扩展字段",
    "时间",
    "zh_text_md5",
};

static std::vector<std::string> LANG_FIELDS = {
    "it_text",
    "zh_text",
    "en_text",
    "ar_text",
    "nl_text",
    "de_text",
    "eo_text",
    "fr_text",
    "he_text",
    "ja_text",
    "pt_text",
    "ru_text",
    "es_text",
    "sv_text",
    "ko_text",
    "th_text",
    "id_text",
    "cht_text",
    "vi_text",
};

static std::vector<std::string> NEW_STYLE_FIELDS = {
    "文件名",
    "是否待查文件",
    "是否重复文件",
    "段落数",
    "去重段落数",
    "低质量段落数",
    "行号",
    "是否重复",
    "是否跨文件重复",
    "it_text",
    "zh_text",
    "en_text",
    "ar_text",
    "nl_text",
    "de_text",
    "eo_text",
    "fr_text",
    "he_text",
    "ja_text",
    "pt_text",
    "ru_text",
    "es_text",
    "sv_text",
    "ko_text",
    "th_text",
    "id_text",
    "cht_text",
    "vi_text",
    "扩展字段",
    "时间",
    "zh_text_md5",
};

// 命令行参数结构
struct Args
{
    std::string input;
    std::string directory;
    bool debug = false;
    bool verbose = false;
    bool disable_rename = false;
};

static Args args;

static void print_usage()
{
    std::cerr << "Usage: postprocess [input.jsonl] [-d directory] [-v] [-dr]\n";
}

static void parse_args(int argc, char **argv)
{
    // 简单解析
    // 可能的参数：
    // 1) postprocess input.jsonl
    // 2) postprocess -d directory
    // 3) -v verbose
    // 4) -dr disable_rename
    for (int i = 1; i < argc; i++)
    {
        std::string a = argv[i];
        if (a == "-d" || a == "--directory")
        {
            if (i + 1 < argc)
            {
                args.directory = argv[++i];
            }
            else
            {
                print_usage();
                exit(1);
            }
        }
        else if (a == "-dbg" || a == "--debug")
        {
            args.debug = true;
        }
        else if (a == "-v" || a == "--verbose")
        {
            args.verbose = true;
        }
        else if (a == "-dr" || a == "--disable_rename")
        {
            args.disable_rename = true;
        }
        else if (args.input.empty() && a[0] != '-')
        {
            args.input = a;
        }
        else
        {
            print_usage();
            exit(1);
        }
    }
}

static std::string md5_hex(const std::string &input)
{
    MD5 md5_calculator;
    return md5_calculator(input.c_str());
}

static std::vector<std::string> scan_filelines(std::vector<std::string> filelines)
{
    // 对filelines进行处理，参考python代码逻辑
    if (args.debug)
        std::cerr << "去除空行以及重复...\n\n";

    // 去除空行以及重复
    {
        // 去空、统一strip，并检查多语言字段全一致的情况
        int64_t lineidx = 0;
        int64_t valid_ptr = 0;
        // std::vector<json> valid_filelines;
        for (auto &flitr : filelines)
        {
            json line = json::parse(flitr);
            std::unordered_set<std::string> line_dedup_set;
            for (auto &f : LANG_FIELDS)
            {
                auto s = line[f].get<std::string>();
                // trim
                {
                    auto &str_ref = s;
                    while (!str_ref.empty() && isspace((unsigned char)str_ref.front()))
                        str_ref.erase(str_ref.begin());
                    while (!str_ref.empty() && isspace((unsigned char)str_ref.back()))
                        str_ref.pop_back();
                }
                line[f] = s;
                line_dedup_set.insert(s);
            }
            flitr = std::move(line.dump(-1, ' ', false, json::error_handler_t::ignore));
            line_dedup_set.erase("");
            if (line_dedup_set.size() <= 1)
            {
                if (args.verbose)
                {
                    std::cerr << "【段落去冗余】为空或不同语种字段全一致的段落:" << line.dump() << "\n";
                }
                // skip
            }
            else
            {
                filelines[valid_ptr++] = filelines[lineidx];
                // valid_filelines.push_back(std::move(line));
            }
            ++lineidx;
        }
        // filelines = std::move(valid_filelines);
        filelines.resize(valid_ptr);
    }
    if (args.debug)
        std::cerr << "文件级去重...\n\n";

    {
        // 文件级去重
        int64_t lineidx = 0;
        int64_t valid_ptr = 0;
        // std::vector<json> valid_filelines;
        std::unordered_set<std::string> dedup_str_set;
        for (auto &flitr : filelines)
        {
            json line = json::parse(flitr);
            json dedup_dict;
            dedup_dict["扩展字段"] = line["扩展字段"];
            for (auto &f : LANG_FIELDS)
            {
                dedup_dict[f] = line[f];
            }
            std::string dedup_str = dedup_dict.dump(-1, ' ', false, json::error_handler_t::ignore);
            if (dedup_str_set.find(dedup_str) == dedup_str_set.end())
            {
                // valid_filelines.push_back(std::move(line));
                filelines[valid_ptr++] = filelines[lineidx];
                dedup_str_set.insert(dedup_str);
            }
            else
            {
                if (args.verbose)
                {
                    std::cerr << "【文件级去重】与其它段落完全一致的段落:" << dedup_str << "\n";
                }
            }
            ++lineidx;
        }
        // filelines = std::move(valid_filelines);
        filelines.resize(valid_ptr);
        filelines.shrink_to_fit();
    }
    if (args.debug)
        std::cerr << "统计重复和低质量...\n\n";
    // 统计重复和低质量
    {
        std::unordered_set<std::string> zh_text_dedup_set;
        int low_quality_count = 0;
        for (auto &flitr : filelines)
        {
            json line = json::parse(flitr);
            std::string zh_text = line["zh_text"];
            std::string en_text = line["en_text"];
            if (zh_text.empty() || en_text.empty())
            {
                low_quality_count++;
            }
            if (zh_text_dedup_set.find(zh_text) != zh_text_dedup_set.end())
            {
                line["是否重复"] = true;
            }
            else
            {
                line["是否重复"] = false;
                zh_text_dedup_set.insert(zh_text);
            }
            flitr = std::move(line.dump(-1, ' ', false, json::error_handler_t::ignore));
        }
        int zh_text_dedup_count = (int)zh_text_dedup_set.size();
        int total = (int)filelines.size();
        // 第二遍填充其他自动字段
        for (int i = 0; i < (int)filelines.size(); i++)
        {
            auto line = json::parse(filelines[i]);
            line["是否待查文件"] = false;
            line["是否重复文件"] = false;
            line["段落数"] = total;
            line["去重段落数"] = total - zh_text_dedup_count;
            line["低质量段落数"] = low_quality_count;
            line["行号"] = i + 1;
            line["是否跨文件重复"] = false;
            {
                // zh_text_md5
                std::string zt = line["zh_text"];
                line["zh_text_md5"] = md5_hex(zt);
            }
            // 确保只保留NEW_STYLE_FIELDS
            json cloned_line;
            for (auto &f : NEW_STYLE_FIELDS)
            {
                cloned_line[f] = line[f];
            }
            // line = std::move(cloned_line);
            filelines[i] = cloned_line.dump(-1, ' ', false, json::error_handler_t::ignore);
        }
    }
    return filelines;
}

static void process_file(const fs::path &file_path)
{
    static bool asked = false;
    // 准备输出目录
    fs::path parent = file_path.parent_path();
    fs::path out_file_dir = parent / "jsonl_reworked";
    fs::path out_file_path = out_file_dir / file_path.filename();

    if (is_first)
    {
        if (fs::exists(out_file_dir))
        {
            std::cerr << "请确保" << out_file_dir.string() << "目录为空，否则其内容可能会被覆盖。如不希望请直接结束本程序。\n";
            std::cerr << "请输入Y以确认继续进行:";
            std::string line;
            std::getline(std::cin, line);
            if (line != "Y")
            {
                std::cerr << "程序退出...\n";
                exit(0);
            }
        }
        else
        {
            fs::create_directories(out_file_dir);
        }
        is_first = false;
    }

    // filename2lines: key=文件名, value=该文件名对应的行集
    std::unordered_map<std::string, std::vector<std::string>> filename2lines;

    // warning maps
    std::unordered_set<std::string> first_warn_unk_key;
    std::unordered_set<std::string> first_warn_other_texts_key_check;

    {
        std::ifstream fi(file_path, std::ios::in);
        if (!fi.is_open())
        {
            std::cerr << "无法打开文件:" << file_path << "\n";
            exit(1);
        }
        int64_t linecounter = 0;
        std::string line;
        while (true)
        {
            ++linecounter;
            if (args.debug && linecounter % 100000 == 0)
                std::cerr << "读取行:" << linecounter << '\n';
            if (!std::getline(fi, line))
                break;
            if (line.empty())
            {
                continue;
            }
            json data;
            try
            {
                data = json::parse(line);
            }
            catch (...)
            {
                std::cerr << "【错误】JSON解析失败:" << line << "\n";
                exit(1);
            }

            if (!args.disable_rename)
            {
                data["文件名"] = file_path.filename().string();
            }

            auto &filelines = filename2lines[data["文件名"].get<std::string>()];

            if (data.find("扩展字段") == data.end())
            {
                // 尝试拓展字段
                if (data.find("拓展字段") != data.end())
                {
                    data["扩展字段"] = data["拓展字段"];
                    data.erase("拓展字段");
                }
                else
                {
                    data["扩展字段"] = "{}";
                }
            }
            if (data["扩展字段"].is_string() && data["扩展字段"].get<std::string>().empty())
            {
                data["扩展字段"] = "{}";
            }

            // 验证扩展字段
            {
                std::string ext_s = data["扩展字段"].get<std::string>();
                json ext_field;
                try
                {
                    ext_field = json::parse(ext_s);
                }
                catch (...)
                {
                    std::cerr << "【错误】扩展字段并非有效json字符串：" << ext_s << "\n";
                    exit(1);
                }
                json accepted_fields;
                if (ext_field.find("other_texts") != ext_field.end())
                {
                    auto other_texts_field = ext_field["other_texts"];
                    for (auto it = other_texts_field.begin(); it != other_texts_field.end(); ++it)
                    {
                        std::string k = it.key();
                        // 长度为2且为小写字母的校验
                        if (k.size() != 2 || !(std::islower((unsigned char)k[0]) && std::islower((unsigned char)k[1])))
                        {
                            if (first_warn_other_texts_key_check.find(k) == first_warn_other_texts_key_check.end())
                            {
                                first_warn_other_texts_key_check.insert(k);
                                std::cerr << "【警告】other_texts含有key名可能不合ISO 639-1规范:" << k << "\n";
                            }
                        }
                    }
                    accepted_fields["other_texts"] = other_texts_field;
                    ext_field.erase("other_texts");
                }
                if (ext_field.find("k") != ext_field.end())
                {
                    accepted_fields["k"] = ext_field["k"];
                    ext_field.erase("k");
                }
                for (auto it = ext_field.begin(); it != ext_field.end(); ++it)
                {
                    std::string unknown_key = it.key();
                    if (first_warn_unk_key.find(unknown_key) == first_warn_unk_key.end())
                    {
                        first_warn_unk_key.insert(unknown_key);
                        std::cerr << "【警告】扩展字段含有尚未定义的字段:" << unknown_key << "\n";
                    }
                    accepted_fields[unknown_key] = it.value();
                }
                data["扩展字段"] = accepted_fields.dump(-1, ' ', false, json::error_handler_t::ignore);
            }

            if (data.find("段落") != data.end())
            {
                // 旧版语料，需要展平
                auto paragraphs = data["段落"];
                json data_cloned = data;
                data_cloned.erase("段落");

                for (auto &p : paragraphs)
                {
                    if (!p.contains("时间") || p["时间"].get<std::string>().empty())
                    {
                        p["时间"] = data["时间"];
                    }
                    if (p.find("扩展字段") == p.end())
                    {
                        if (p.find("拓展字段") != p.end())
                        {
                            p["扩展字段"] = p["拓展字段"];
                            p.erase("拓展字段");
                        }
                        else
                        {
                            p["扩展字段"] = "{}";
                        }
                    }
                    if (p["扩展字段"].is_string() && p["扩展字段"].get<std::string>().empty())
                    {
                        p["扩展字段"] = "{}";
                    }

                    if (p.find("other1_text") != p.end())
                    {
                        if (!p["other1_text"].get<std::string>().empty())
                        {
                            std::cerr << "【错误】段落" << p["行号"] << "中存在other1_text字段，请确认具体是哪种语言并放入扩展字段中" << p.dump() << "\n";
                            exit(1);
                        }
                    }
                    if (p.find("other2_text") != p.end())
                    {
                        if (!p["other2_text"].get<std::string>().empty())
                        {
                            std::cerr << "【错误】段落" << p["行号"] << "中存在other2_text字段，请确认具体是哪种语言并放入扩展字段中" << p.dump() << "\n";
                            exit(1);
                        }
                    }
                    // 验证段落扩展字段
                    {
                        std::string ext_s = p["扩展字段"].get<std::string>();
                        json ext_field;
                        try
                        {
                            ext_field = json::parse(ext_s);
                        }
                        catch (...)
                        {
                            std::cerr << "【错误】扩展字段并非有效json字符串：" << p.dump() << "\n";
                            exit(1);
                        }
                        p["扩展字段"] = ext_field.dump(-1, ' ', false, json::error_handler_t::ignore);
                    }

                    for (auto &f : LANG_FIELDS)
                    {
                        if (!p.contains(f))
                        {
                            p[f] = "";
                        }
                    }
                    json merged = data_cloned;
                    for (auto &k : KEEP_KEYS)
                    {
                        merged[k] = p[k];
                    }
                    filelines.push_back(merged.dump(-1, ' ', false, json::error_handler_t::ignore));
                    merged.clear();
                }
            }
            else
            {
                // 新版语料行
                filelines.push_back(data.dump(-1, ' ', false, json::error_handler_t::ignore));
                data.clear();
            }
        }
    }

    // 输出处理
    {
        std::ofstream fo(out_file_path, std::ios::out | std::ios::trunc);
        if (!fo.is_open())
        {
            std::cerr << "无法创建输出文件:" << out_file_path << "\n";
            exit(1);
        }

        // 处理filename2lines
        for (auto &kv : filename2lines)
        {
            std::string filename = kv.first;
            auto &flines = kv.second;
            auto processed = scan_filelines(std::move(flines));
            for (auto &ln : processed)
            {
                // fo << ln.dump(-1, ' ', false, json::error_handler_t::ignore) << "\n";
                fo << ln << "\n";
            }
            processed.clear();
        }
    }
}

int main(int argc, char **argv)
{
    parse_args(argc, argv);

    if (args.directory.empty() && args.input.empty())
    {
        std::cerr << "请提供一个目录或输入文件路径。\n";
        exit(0);
    }

    if (!args.directory.empty())
    {
        // 目录处理
        for (auto &p : fs::directory_iterator(args.directory))
        {
            if (!p.is_regular_file())
                continue;
            auto ext = p.path().extension();
            if (ext == ".jsonl")
            {
                std::cerr << "[directory] filename:" << p.path().filename().string() << "\n";
                process_file(p.path());
            }
        }
    }
    else
    {
        // 单文件处理
        std::cerr << "[single file] filename:" << args.input << "\n";
        process_file(args.input);
    }

    std::cerr << "处理完毕，按回车关闭\n";
    {
        std::string dummy;
        std::getline(std::cin, dummy);
    }

    return 0;
}
