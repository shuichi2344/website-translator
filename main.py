import flet as ft
import pycountry

country_list = sorted([c.name for c in pycountry.countries])
country_options = [ft.dropdown.Option(name) for name in country_list]

def main(page: ft.Page):
    # Responsive Configuration
    page.title = "AI Chat App"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0B0E14"
    
    # This allows the app to adapt to the window size
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    state = {"is_signup": False}

    def chat_bubble(message, is_user=True):
        return ft.Container(
            content=ft.Text(message, color=ft.colors.WHITE),
            alignment=ft.alignment.center_right if is_user else ft.alignment.center_left,
            padding=12,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=["#8E2DE2", "#4A00E0"] if is_user else ["#1A1D26", "#252936"],
            ),
            border_radius=ft.border_radius.only(
                top_left=18, top_right=18, 
                bottom_left=18 if is_user else 4, 
                bottom_right=4 if is_user else 18
            ),
            shadow=ft.BoxShadow(
                spread_radius=1, blur_radius=10,
                color=ft.colors.with_opacity(0.3, "#8E2DE2") if is_user else ft.colors.BLACK12,
            ),
            # Use relative margins for responsiveness
            margin=ft.margin.only(left=page.window_width*0.15 if is_user else 10, 
                                 right=10 if is_user else page.window_width*0.15, 
                                 bottom=10),
        )

    def route_change(e):
        page.views.clear()
        
        # Responsive Width Constraint (Max 500px for readability on desktop)
        content_width = min(page.window_width * 0.9, 450)

        if page.route == "/login":
            title_text = "CREATE NEW ACCOUNT" if state["is_signup"] else "LOGIN TO YOUR ACCOUNT"
            button_text = "REGISTER" if state["is_signup"] else "LOGIN"
            toggle_text = "Already have an account? Login" if state["is_signup"] else "New user? Create a new account"

            def handle_submit(e):
                if state["is_signup"]:
                    # LEGACY SNACKBAR METHOD
                    page.snack_bar = ft.SnackBar(
                        ft.Text("Registration successful! Please login."),
                        bgcolor="#4A00E0"
                    )
                    page.snack_bar.open = True
                    page.update() # Required in older versions
                    
                    state["is_signup"] = False
                    route_change(None)
                else:
                    page.snack_bar = ft.SnackBar(
                        ft.Text("Login successful! Welcome."),
                        bgcolor="#8E2DE2"
                    )
                    page.snack_bar.open = True
                    # Force the update to show the SnackBar immediately
                    page.update()
                    
                    # Small logic check: verify the route is actually changing
                    print("Attempting to go home...")
                    page.go("/home")

            def toggle_mode(e):
                state["is_signup"] = not state["is_signup"]
                route_change(None)

            # Define fields explicitly here
            fields = [
                ft.Icon(ft.icons.LOCK_PERSON_ROUNDED, size=80, color="#A29BFE"),
                ft.TextField(label="Username", border_color="#4A00E0", border_radius=15, width=content_width),
                ft.TextField(label="Password", password=True, can_reveal_password=True, border_color="#4A00E0", border_radius=15, width=content_width),
            ]

            if state["is_signup"]:
                fields.append(
                    ft.Dropdown(
                        label="Country",
                        options=country_options,
                        border_color="#4A00E0",
                        border_radius=15,
                        width=content_width,
                    )
                )
                fields.extend([
                    ft.Divider(height=10, color="transparent"),
                    ft.Text("SYSTEM PERMISSIONS", color="#A29BFE", size=12, weight="bold"),
                    ft.Row([
                        ft.Switch(label="Mic", value=True, active_color="#8E2DE2"),
                        ft.Switch(label="Plugins", value=False, active_color="#00D2FF"),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                ])

            fields.extend([
                ft.Divider(height=10, color="transparent"),
                ft.ElevatedButton(
                    button_text, 
                    on_click=handle_submit,
                    style=ft.ButtonStyle(color=ft.colors.WHITE, bgcolor="#4A00E0", shape=ft.RoundedRectangleBorder(radius=12)),
                    width=content_width, height=50
                ),
                ft.TextButton(toggle_text, on_click=toggle_mode, style=ft.ButtonStyle(color="#A29BFE"))
            ])

            page.views.append(
                ft.View(
                    "/login",
                    [
                        ft.AppBar(title=ft.Text(title_text), bgcolor="#11141C", center_title=True),
                        ft.Container(
                            content=ft.Column(fields, tight=True, spacing=15, horizontal_alignment="center"),
                            alignment=ft.alignment.center,
                            expand=True
                        )
                    ],
                    bgcolor="#0B0E14"
                )
            )

        elif page.route == "/home":
            chat_list = ft.ListView(expand=True, spacing=15, padding=20, auto_scroll=True)
            chat_list.controls.append(chat_bubble("Neural connection established. Select method.", is_user=False))

            # --- Helper to create cards like your reference ---
            def create_option_card(title, desc, icon, color, mode):
                return ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(icon, color=color, size=30),
                            ft.Text(title, size=22, weight="bold", color=ft.colors.WHITE),
                        ], alignment=ft.MainAxisAlignment.START, spacing=10),
                        ft.Text(desc, size=14, color="#A29BFE"),
                    ], spacing=10),
                    width=280,
                    height=180,
                    padding=25,
                    border=ft.border.all(2, color if mode == "file" else "#333742"),
                    border_radius=15,
                    bgcolor="#1A1D26",
                    on_click=lambda _: enter_focused_mode(mode),
                )

            # --- UI References ---
            # 1. The Card Selection (Visible first)
            main_selection = ft.Column([
                ft.Text("Let's build", size=40, weight="bold", color=ft.colors.WHITE),
                ft.Text("Plan, search, or build anything", size=16, color="#A29BFE"),
                ft.Divider(height=20, color="transparent"),
                ft.Row([
                    create_option_card("File", "Chat first, then build.\nExplore ideas and data.", ft.icons.CHAT_OUTLINED, "#8E2DE2", "file"),
                    create_option_card("Web", "Plan first, then build.\nAnalyze web links and code.", ft.icons.GRID_VIEW_ROUNDED, "#00D2FF", "web"),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

            # 2. Focused Task Area (Hidden initially)
            task_title = ft.Text("", size=24, weight="bold", color=ft.colors.WHITE)
            file_upload_ui = ft.Container(
                content=ft.ElevatedButton("SELECT LOCAL FILE", icon=ft.icons.ATTACH_FILE),
                visible=False, padding=20
            )
            web_link_ui = ft.TextField(label="Paste URL Link", border_color="#00D2FF", visible=False, width=400)
            
            user_question = ft.TextField(
                hint_text="Ask about this data...", 
                border_radius=15, 
                bgcolor="#1A1D26",
                width=500
            )
            
            summary_box = ft.Container(
                content=ft.Text("Neural processing complete. Summary ready.", italic=True, color="#00D2FF"),
                padding=20, bgcolor="#0B0E14", border_radius=10, visible=False, width=500
            )

            # --- Logic Functions ---
            def enter_focused_mode(mode):
                main_selection.visible = False
                mic_button.visible = False # Remove mic as requested
                focused_view.visible = True
                if mode == "file":
                    task_title.value = "File Analysis Mode"
                    file_upload_ui.visible = True
                    web_link_ui.visible = False
                else:
                    task_title.value = "Web Analytics Mode"
                    file_upload_ui.visible = False
                    web_link_ui.visible = True
                page.update()

            def exit_focused_mode():
                main_selection.visible = True
                mic_button.visible = True
                focused_view.visible = False
                summary_box.visible = False
                page.update()

            focused_view = ft.Column([
                task_title,
                file_upload_ui,
                web_link_ui,
                user_question,
                ft.ElevatedButton("SUBMIT TO CORE", bgcolor="#4A00E0", color="white", width=200, 
                                  on_click=lambda _: [setattr(summary_box, 'visible', True), page.update()]),
                summary_box,
                ft.TextButton("Cancel / Back", on_click=lambda _: exit_focused_mode(), style=ft.ButtonStyle(color=ft.colors.RED_400))
            ], visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20)

            mic_button = ft.FloatingActionButton(icon=ft.icons.MIC_ROUNDED, bgcolor="#4A00E0")

            # --- Page Construction ---
            page.views.append(
                ft.View(
                    "/home",
                    [
                        ft.AppBar(title=ft.Text("CYBER CORE"), bgcolor="#11141C", center_title=True),
                        ft.Container(content=chat_list, expand=True),
                        ft.Container(
                            padding=40,
                            bgcolor="#11141C",
                            width=1000,
                            content=ft.Column([
                                main_selection,
                                focused_view,
                                ft.Divider(height=20, color="transparent"),
                                mic_button 
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            alignment=ft.alignment.center
                        )
                    ],
                    padding=0, bgcolor="#0B0E14"
                )
            )

        elif page.route == "/profile":
            # Profile UI Elements
            profile_fields = [
                ft.CircleAvatar(
                    content=ft.Icon(ft.icons.PERSON_ROUNDED, size=40),
                    radius=50,
                    bgcolor="#4A00E0",
                ),
                ft.Text("USER_01 // CYBER_CORE", size=20, weight="bold", color="#A29BFE"),
                ft.Divider(height=20, color="transparent"),
                
                # Stats/Info Cards
                ft.Container(
                    content=ft.Column([
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.EMAIL_ROUNDED, color="#00D2FF"),
                            title=ft.Text("Email Address"),
                            subtitle=ft.Text("user@cybercore.net", color="#A29BFE"),
                        ),
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.SHIELD_ROUNDED, color="#8E2DE2"),
                            title=ft.Text("Security Level"),
                            subtitle=ft.Text("Level 4 Clearances", color="#A29BFE"),
                        ),
                    ]),
                    bgcolor="#1A1D26",
                    border_radius=15,
                    padding=10,
                    width=content_width
                ),
                
                ft.Divider(height=20, color="transparent"),
                
                # Logout Button
                ft.ElevatedButton(
                    "LOGOUT",
                    icon=ft.icons.LOGOUT_ROUNDED,
                    on_click=lambda _: page.go("/login"),
                    style=ft.ButtonStyle(
                        color=ft.colors.WHITE, 
                        bgcolor="#B22222", # Dark Red for logout
                        shape=ft.RoundedRectangleBorder(radius=12)
                    ),
                    width=content_width,
                    height=50
                ),
                
                ft.TextButton(
                    "Back to Terminal", 
                    on_click=lambda _: page.go("/home"),
                    style=ft.ButtonStyle(color="#A29BFE")
                )
            ]

            page.views.append(
                ft.View(
                    "/profile",
                    [
                        ft.AppBar(
                            title=ft.Text("USER PROFILE"), 
                            bgcolor="#11141C", 
                            center_title=True,
                            # Add a back button manually for safety
                            leading=ft.IconButton(
                                ft.icons.ARROW_BACK_ROUNDED, 
                                on_click=lambda _: page.go("/home")
                            )
                        ),
                        ft.Container(
                            content=ft.Column(
                                profile_fields, 
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=10
                            ),
                            alignment=ft.alignment.center,
                            expand=True,
                            padding=20
                        )
                    ],
                    bgcolor="#0B0E14"
                )
            )
        # (Profile view remains similar, ensured with alignment=ft.alignment.center)
        page.update()

    page.on_route_change = route_change
    # Trigger refresh on resize
    page.on_resize = lambda _: page.update()
    page.go("/login")

ft.app(target=main)