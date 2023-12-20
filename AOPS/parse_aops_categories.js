const categories = []

for (let cate of AoPS.Community.categories) {
    if(cate.category_type != "forum" && cate.category_type != "folder" && cate.category_type != "folder_collections") {
        continue
    }
    if(cate.category_name == "AoPS Collection" || cate.category_name == "2023 Contests") {
        continue
    }
    let categorie = {}
    categorie.category_id = cate.category_id
    categorie.category_name = cate.category_name
    categorie.category_type = cate.category_type
    categorie.num_posts = cate.num_posts
    categorie.num_topics = cate.num_topics
    categorie.num_users = cate.num_users
    if(cate.category_type != "forum"){
        categorie.items = []
        for(let i of cate.items) {
            if("category" in i) {
                delete i.category
            }
            categorie.items.push(i)
        }
    }
    categories.push(categorie)
}
JSON.stringify(categories)