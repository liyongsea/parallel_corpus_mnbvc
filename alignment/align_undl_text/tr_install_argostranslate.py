import argostranslate.package
import argostranslate.translate

# NEED_TARGETS = ('es', 'zh', 'fr', 'ru', 'ar', 'de')
NEED_TARGETS = ('zh',)

def install_translator():
    # 经测试开系统代理下包可行
    installed = argostranslate.package.get_installed_packages()
    print(installed)
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    print(available_packages)
    for i in filter(lambda x: x.from_code == 'en' and x.to_code in NEED_TARGETS, available_packages):
        if i in installed:
            print('skip', i)
            continue
        print('install', i)
        i.install()

if __name__ == '__main__':
    install_translator()