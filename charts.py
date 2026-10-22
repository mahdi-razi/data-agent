import os


def save_chart(fig, name, folder="outputs"):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name + ".html")
    fig.write_html(path, include_plotlyjs="cdn")
    return path