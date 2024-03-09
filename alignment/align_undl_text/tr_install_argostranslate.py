import argostranslate.package
import argostranslate.translate
import os
# NEED_TARGETS = ('es', 'zh', 'fr', 'ru', 'ar', 'de')
NEED_TARGETS = ('en',)

def install_translator(needs = NEED_TARGETS):
    # 经测试开系统代理下包可行
    installed = argostranslate.package.get_installed_packages()
    print(installed)
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    print(available_packages)
    for i in filter(lambda x: x.from_code == 'ar' and x.to_code in needs, available_packages):
        if i in installed:
            print('skip', i)
            continue
        print('install', i)
        i.install()

def install_local():
    for i in os.listdir('.'):
        if i.endswith('.argosmodel'):
            argostranslate.package.install_from_path(i)

if __name__ == '__main__':
    # install_translator()
    install_local()