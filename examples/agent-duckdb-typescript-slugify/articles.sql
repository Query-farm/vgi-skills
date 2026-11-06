SELECT title, demo.main.slugify(title) AS slug
FROM read_csv('articles.csv')
ORDER BY id;
