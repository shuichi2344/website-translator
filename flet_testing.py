import flet as ft
from flet_STT import create_session
from main import process_voice_result

def main(page: ft.Page):
    page.title = "Voice Assistant"

    session, stream = create_session()

    status_text = ft.Text("Hold button to speak")
    result_text = ft.Text("")
    response_text = ft.Text("")  # 👈 response from main.py

    def on_press(e):
        status_text.value = "🎤 Recording..."
        page.update()

        stream.start()
        session.start_recording()

    def on_release(e):
        status_text.value = "⏳ Processing..."
        page.update()

        session.stop_recording()
        stream.stop()

        results = session.results

        dialect = results.get("dialect")
        question = results.get("question")
        query = results.get("query")

        # 👇 CALL main.py FUNCTION HERE
        response = process_voice_result(dialect, question, query)

        result_text.value = (
            f"Dialect: {dialect}\n"
            f"Question: {question}\n"
            f"Query: {query}"
        )

        response_text.value = f"Response: {response}"

        status_text.value = "✅ Done!"
        page.update()

    mic_button = ft.GestureDetector(
        on_tap_down=on_press,
        on_tap_up=on_release,
        content=ft.Container(
            content=ft.Text("🎤 Hold to Talk"),
            padding=20,
            bgcolor=ft.colors.BLUE,
            border_radius=10
        )
    )

    page.add(
        mic_button,
        status_text,
        result_text,
        response_text
    )

ft.app(target=main)