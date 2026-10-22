import os


def make_path(name, folder):
    if not name.replace("_", "").isalnum():
        raise ValueError("name must contain only letters, digits and underscores, like sales_by_region")

    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, name + ".html")


def save_chart(fig, name, folder="outputs"):
    path = make_path(name, folder)
    fig.write_html(path, include_plotlyjs="cdn")
    return path