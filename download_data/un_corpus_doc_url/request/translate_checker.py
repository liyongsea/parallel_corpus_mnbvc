import datasets
import const

ds = datasets.load_from_disk(const.CONVERT_DATASET_CACHE_DIR)

print(len(ds), ds.column_names)

fds = ds.filter(lambda x: x['record'] == "A/78/5/ADD.1_5463717")
print(fds[0])
# print(len(fds[0]['']))