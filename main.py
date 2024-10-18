import os
import logging
import aiohttp
import asyncio
import flet as ft
from urllib.parse import unquote

logging.basicConfig(filename="logs.txt", level=logging.INFO, encoding='utf-8')


def get_file_id(url):
    if 'id=' in url:
        return url.split('id=')[-1].split('&')[0]
    elif '/d/' in url:
        return url.split('/d/')[-1].split('/')[0]
    return None


async def download_file(session, url, destination_folder, link_status_row, page):
    try:
        file_id = get_file_id(url)
        if not file_id:
            logging.error(f"Unable to extract file IDs from the link: {url}")
            link_status_row.controls[0] = ft.Icon(name=ft.icons.CLOSE, color="red")
            link_status_row.update()
            return

        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

        async with session.get(download_url) as response:
            if response.status == 200:
                content_disposition = response.headers.get('content-disposition')
                if content_disposition:
                    filename = unquote(content_disposition.split('filename=')[-1].strip('\"'))
                else:
                    filename = f"{file_id}.file"

                filename = "".join([c for c in filename if c not in '<>:"/\\|?*'])
                destination = os.path.join(destination_folder, filename)

                try:
                    with open(destination, 'wb') as file:
                        async for chunk in response.content.iter_chunked(1024):
                            file.write(chunk)
                    logging.info(f"File saved: {destination}")
                    link_status_row.controls[0] = ft.Icon(name=ft.icons.CHECK, color="green")
                    link_status_row.controls[2] = ft.Text("")
                    link_status_row.update()
                    snack_bar = ft.SnackBar(ft.Text("Download completed!"), open=True)
                    page.overlay.append(snack_bar)
                    page.update()
                except IOError as e:
                    logging.error(f"Writing file error {filename}: {e}")
                    link_status_row.controls[0] = ft.Icon(name=ft.icons.CLOSE, color="red")
                    link_status_row.controls[2] = ft.Text("")
                    link_status_row.update()
            else:
                logging.warning(f"Unable to download a file (HTTP {response.status}): {url}")
                link_status_row.controls[0] = ft.Icon(name=ft.icons.CLOSE, color="red")
                link_status_row.controls[2] = ft.Text("")
                link_status_row.update()
    except aiohttp.ClientError as e:
        logging.error(f"HTTP error during downloading {url}: {e}")
        link_status_row.controls[0] = ft.Icon(name=ft.icons.CLOSE, color="red")
        link_status_row.controls[2] = ft.Text("")
        link_status_row.update()
    except Exception as e:
        logging.error(f"Unexpected error during downloading {url}: {e}", exc_info=True)
        link_status_row.controls[0] = ft.Icon(name=ft.icons.CLOSE, color="red")
        link_status_row.controls[2] = ft.Text("")
        link_status_row.update()


async def download_all_files(links, destination_folder, links_container, page):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for link in links:
            if link.strip():
                link_status_row = ft.Row([
                    ft.Icon(name=ft.icons.DOWNLOADING, color=ft.colors.SURFACE_TINT),
                    ft.TextButton(
                        content=ft.Text(link, selectable=True),
                        on_click=lambda e, link=link: page.launch_url(link)
                    ),
                    ft.ProgressRing(width=16, height=16, stroke_width=2)
                ], alignment=ft.MainAxisAlignment.CENTER)
                links_container.controls.append(link_status_row)
                page.update()
                task = download_file(session, link, destination_folder, link_status_row, page)
                tasks.append(task)
        await asyncio.gather(*tasks)
        links.clear()
        tasks.clear()


def main(page: ft.Page):
    page.title = "Google Drive File Downloader by ©Daniel K"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.theme_mode = 'dark'
    page.fonts = {'Sofia Sans': 'SofiaSans-VariableFont_wght.ttf'}
    page.theme = ft.Theme(font_family='Sofia Sans')

    links_text = ft.TextField(label="Paste a links to files (one at row):", multiline=True, min_lines=1,
                              max_lines=5, expand=True, autofocus=True)

    file_picker = ft.FilePicker(on_result=lambda e: print(e.path))
    page.overlay.append(file_picker)

    def change_theme(e):
        page.theme_mode = 'light' if page.theme_mode == 'dark' else 'dark'
        lightbulb_icon.icon = (ft.icons.LIGHTBULB
                               if lightbulb_icon.icon == ft.icons.LIGHTBULB_OUTLINE else ft.icons.LIGHTBULB_OUTLINE)
        page.update()

    links_container = ft.Column(scroll="always", expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    async def download_button_clicked(e):
        links = links_text.value.splitlines()
        links_text.value = ""
        page.update()

        file_picker.get_directory_path(dialog_title="Choose destination folder:")

        async def on_directory_pick_result(e: ft.FilePickerResultEvent):
            if e.path:
                links_container.controls.clear()
                destination_folder = e.path
                os.makedirs(destination_folder, exist_ok=True)
                await download_all_files(links, destination_folder, links_container, page)

        file_picker.on_result = on_directory_pick_result

    download_button = ft.ElevatedButton("Download files", on_click=download_button_clicked, width=250, height=50)
    lightbulb_icon = ft.IconButton(ft.icons.LIGHTBULB_OUTLINE, on_click=change_theme)

    page.add(
        ft.Row([lightbulb_icon,
                ft.Text('Google Drive File Downloader', weight=ft.FontWeight.BOLD, size=20)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Row([links_text], alignment=ft.MainAxisAlignment.CENTER),
        ft.Row([download_button], alignment=ft.MainAxisAlignment.CENTER),
        links_container
    )


ft.app(target=main, assets_dir="assets")
