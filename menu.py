from pyrogram import types
from filters import FilterConfig, MediaType, SourceConfig, TargetConfig

PAGE_SIZE = 5

# ============ MAIN MENU ============


def build_main_menu_keyboard():
    """Main menu with quick access"""
    keyboard = [
        [types.InlineKeyboardButton("📂 Quản lý Target", callback_data="menu_targets")],
        [
            types.InlineKeyboardButton("📹 Video", callback_data="main_video"),
            types.InlineKeyboardButton("📷 Ảnh", callback_data="main_photo"),
            types.InlineKeyboardButton("📄 Doc", callback_data="main_doc"),
        ],
        [
            types.InlineKeyboardButton("⏱ Duration", callback_data="main_duration"),
            types.InlineKeyboardButton("⚡ Realtime", callback_data="main_realtime"),
        ],
        [types.InlineKeyboardButton("📊 Thống kê", callback_data="menu_stats")],
    ]
    return types.InlineKeyboardMarkup(keyboard)


# ============ TARGET LIST ============


def build_target_keyboard(user_id: int, page: int = 0):
    """Build keyboard showing targets with their sources"""
    targets = TargetConfig.get_all(user_id)
    total_pages = max(1, (len(targets) + PAGE_SIZE - 1) // PAGE_SIZE)

    keyboard = []

    # Header
    keyboard.append(
        [types.InlineKeyboardButton("📂 DANH SÁCH TARGET", callback_data="noop")]
    )

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE

    for target in targets[start:end]:
        sources = target.get_sources()
        enabled_count = sum(1 for s in sources if s.enabled)
        status = "🟢" if target.enabled else "🔴"

        # Target row - show target and source count
        keyboard.append(
            [
                types.InlineKeyboardButton(
                    f"{status} {target.name} ({len(sources)} nguồn)",
                    callback_data=f"target_view_{target.target_chat_id}",
                )
            ]
        )

        # Show first 3 sources inline
        for src in sources[:3]:
            src_status = "🟢" if src.enabled else "🔴"
            filter_cfg = FilterConfig.get(user_id, src.source_chat_id)
            media_icon = get_media_icon(filter_cfg.media_types)
            keyboard.append(
                [
                    types.InlineKeyboardButton(
                        f"  {src_status} {media_icon} {src.source_chat_id}",
                        callback_data=f"src_edit_{src.source_chat_id}",
                    )
                ]
            )

        if len(sources) > 3:
            keyboard.append(
                [
                    types.InlineKeyboardButton(
                        f"  +{len(sources) - 3} nguồn khác...",
                        callback_data=f"target_view_{target.target_chat_id}",
                    )
                ]
            )

        # Action row for target
        keyboard.append(
            [
                types.InlineKeyboardButton(
                    "➕ Thêm nguồn",
                    callback_data=f"target_add_src_{target.target_chat_id}",
                ),
                types.InlineKeyboardButton(
                    "⚙️", callback_data=f"target_config_{target.target_chat_id}"
                ),
                types.InlineKeyboardButton(
                    "🗑️", callback_data=f"target_del_{target.target_chat_id}"
                ),
            ]
        )

    # Navigation
    nav = []
    if page > 0:
        nav.append(
            types.InlineKeyboardButton("◀", callback_data=f"target_page_{page - 1}")
        )
    nav.append(
        types.InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop")
    )
    if page < total_pages - 1:
        nav.append(
            types.InlineKeyboardButton("▶", callback_data=f"target_page_{page + 1}")
        )

    if nav:
        keyboard.append(nav)

    # Add new target
    keyboard.append(
        [types.InlineKeyboardButton("➕ Thêm Target mới", callback_data="target_add")]
    )

    # Back
    keyboard.append(
        [types.InlineKeyboardButton("🔙 Quay lại", callback_data="menu_main")]
    )

    return types.InlineKeyboardMarkup(keyboard)


def get_media_icon(media_types: list) -> str:
    """Get icon for media types"""
    if MediaType.ALL in media_types:
        return "📺"
    if MediaType.VIDEO in media_types:
        return "📹"
    if MediaType.PHOTO in media_types:
        return "📷"
    if MediaType.DOCUMENT in media_types:
        return "📄"
    if MediaType.AUDIO in media_types:
        return "🔊"
    return "📝"


# ============ TARGET DETAIL ============


def build_target_detail_keyboard(user_id: int, target_chat_id: int):
    """Show all sources under a target"""
    target = TargetConfig.get(user_id, target_chat_id)
    if not target:
        return build_target_keyboard(user_id)

    sources = target.get_sources()

    keyboard = []

    # Header
    status = "🟢" if target.enabled else "🔴"
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"{status} 📂 {target.name}",
                callback_data=f"target_toggle_{target_chat_id}",
            )
        ]
    )

    # List all sources
    keyboard.append([types.InlineKeyboardButton("📨 NGUỒN:", callback_data="noop")])

    for src in sources:
        filter_cfg = FilterConfig.get(user_id, src.source_chat_id)
        src_status = "🟢" if src.enabled else "🔴"
        media_icon = get_media_icon(filter_cfg.media_types)

        min_dur = filter_cfg.min_duration or 0
        max_dur = filter_cfg.max_duration or "∞"

        keyboard.append(
            [
                types.InlineKeyboardButton(
                    f"{src_status} {media_icon} {src.source_chat_id}",
                    callback_data=f"src_edit_{src.source_chat_id}",
                ),
                types.InlineKeyboardButton(
                    f"⏱{min_dur}-{max_dur}",
                    callback_data=f"src_dur_{src.source_chat_id}",
                ),
                types.InlineKeyboardButton(
                    "❌", callback_data=f"src_del_{src.source_chat_id}"
                ),
            ]
        )

    # Actions
    keyboard.append(
        [
            types.InlineKeyboardButton(
                "➕ Thêm nguồn vào target",
                callback_data=f"target_add_src_{target_chat_id}",
            )
        ]
    )
    keyboard.append(
        [
            types.InlineKeyboardButton(
                "🎯 Set all sources → Video",
                callback_data=f"target_set_video_{target_chat_id}",
            )
        ]
    )
    keyboard.append(
        [
            types.InlineKeyboardButton(
                "📷 Set all sources → Ảnh",
                callback_data=f"target_set_photo_{target_chat_id}",
            )
        ]
    )
    keyboard.append(
        [types.InlineKeyboardButton("🔙 Quay lại", callback_data="menu_targets")]
    )

    return types.InlineKeyboardMarkup(keyboard)


# ============ FILTER CONFIG ============


def build_filter_keyboard(user_id: int, source_chat_id: int):
    """Build filter config keyboard for a source"""
    filter_config = FilterConfig.get(user_id, source_chat_id)
    source_config = SourceConfig.get(user_id, source_chat_id)

    if not source_config:
        return build_target_keyboard(user_id)

    target = TargetConfig.get(user_id, source_config.target_chat_id)

    keyboard = []

    # Header
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"⚙️ {source_chat_id} → {source_config.target_chat_id}",
                callback_data="noop",
            )
        ]
    )

    # Enable/Disable
    status = "🔴 TẮT" if filter_config.enabled else "🟢 BẬT"
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"▶️ {status}", callback_data=f"filter_toggle_{source_chat_id}"
            )
        ]
    )

    # Media types
    keyboard.append(
        [types.InlineKeyboardButton("📨 LOẠI TIN NHẮN", callback_data="noop")]
    )

    v_check = (
        "✅"
        if MediaType.VIDEO in filter_config.media_types
        or MediaType.ALL in filter_config.media_types
        else "⬜"
    )
    p_check = (
        "✅"
        if MediaType.PHOTO in filter_config.media_types
        or MediaType.ALL in filter_config.media_types
        else "⬜"
    )
    d_check = (
        "✅"
        if MediaType.DOCUMENT in filter_config.media_types
        or MediaType.ALL in filter_config.media_types
        else "⬜"
    )
    a_check = (
        "✅"
        if MediaType.AUDIO in filter_config.media_types
        or MediaType.ALL in filter_config.media_types
        else "⬜"
    )
    t_check = (
        "✅"
        if MediaType.TEXT in filter_config.media_types
        or MediaType.ALL in filter_config.media_types
        else "⬜"
    )

    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"{v_check} Video", callback_data=f"media_toggle_video_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                f"{p_check} Ảnh", callback_data=f"media_toggle_photo_{source_chat_id}"
            ),
        ]
    )
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"{d_check} Tài liệu",
                callback_data=f"media_toggle_document_{source_chat_id}",
            ),
            types.InlineKeyboardButton(
                f"{a_check} Audio", callback_data=f"media_toggle_audio_{source_chat_id}"
            ),
        ]
    )
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"{t_check} Text", callback_data=f"media_toggle_text_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "🔄 All", callback_data=f"media_all_{source_chat_id}"
            ),
        ]
    )

    # Duration
    keyboard.append(
        [types.InlineKeyboardButton("⏱ THỜI LƯỢNG (giây)", callback_data="noop")]
    )

    min_dur = filter_config.min_duration or 0
    max_dur = filter_config.max_duration or "∞"

    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"Min: {min_dur}s", callback_data=f"dur_min_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                f"Max: {max_dur}s", callback_data=f"dur_max_{source_chat_id}"
            ),
        ]
    )

    # Quick presets
    keyboard.append(
        [
            types.InlineKeyboardButton(
                "1p+", callback_data=f"dur_preset_60_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "3p+", callback_data=f"dur_preset_180_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "5p+", callback_data=f"dur_preset_300_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "Bỏ limit", callback_data=f"dur_clear_{source_chat_id}"
            ),
        ]
    )

    # Back
    keyboard.append(
        [
            types.InlineKeyboardButton(
                "🔙 Quay lại",
                callback_data=f"target_view_{source_config.target_chat_id}",
            )
        ]
    )

    return types.InlineKeyboardMarkup(keyboard)


# ============ REALTIME & STATS ============


def build_realtime_keyboard(user_id: int):
    keyboard = [
        [types.InlineKeyboardButton("▶️ BẬT REALTIME", callback_data="realtime_on")],
        [types.InlineKeyboardButton("⏹ TẮT REALTIME", callback_data="realtime_off")],
        [types.InlineKeyboardButton("🔙 Quay lại", callback_data="menu_main")],
    ]
    return types.InlineKeyboardMarkup(keyboard)


def build_stats_keyboard(user_id: int):
    keyboard = [
        [types.InlineKeyboardButton("🔄 Làm mới", callback_data="menu_stats")],
        [types.InlineKeyboardButton("🔙 Quay lại", callback_data="menu_main")],
    ]
    return types.InlineKeyboardMarkup(keyboard)


# ============ CALLBACK HANDLER ============


async def handle_callback(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id

    if data == "noop":
        await callback_query.answer()
        return

    # === MAIN MENU ===
    if data == "menu_main":
        await callback_query.message.edit(
            "⚙️ **Menu cấu hình:**",
            reply_markup=build_main_menu_keyboard(),
            parse_mode="markdown",
        )
        await callback_query.answer()
        return

    if data == "menu_targets":
        await callback_query.message.edit(
            "📂 **Danh sách Target:**",
            reply_markup=build_target_keyboard(user_id),
            parse_mode="markdown",
        )
        await callback_query.answer()
        return

    if data == "menu_stats":
        from sync import forwarded_messages

        total = forwarded_messages.count_documents({"user_id": user_id})
        targets = TargetConfig.get_all(user_id)
        sources = SourceConfig.get_all(user_id)
        enabled_sources = sum(1 for s in sources if s.enabled)

        media_stats = {}
        for doc in forwarded_messages.find({"user_id": user_id}):
            mt = doc.get("media_type", "unknown")
            media_stats[mt] = media_stats.get(mt, 0) + 1

        from bot import realtime_running

        rt_status = "✅ Đang chạy" if realtime_running.get(user_id) else "❌ Đã dừng"

        text = f"""📊 **Thống kê**

• Tổng tin nhắn: **{total}**
• Targets: **{len(targets)}**
• Nguồn: **{len(sources)}** (🟢 {enabled_sources} / 🔴 {len(sources) - enabled_sources})
• Realtime: **{rt_status}**

**Theo loại:**
📹 Video: {media_stats.get("video", 0)}
📷 Ảnh: {media_stats.get("photo", 0)}
📄 Doc: {media_stats.get("document", 0)}
🔊 Audio: {media_stats.get("audio", 0)}
"""

        await callback_query.message.edit(
            text, reply_markup=build_stats_keyboard(user_id), parse_mode="markdown"
        )
        await callback_query.answer()
        return

    # === TARGET PAGINATION ===
    if data.startswith("target_page_"):
        page = int(data.split("_")[-1])
        await callback_query.message.edit(
            "📂 **Danh sách Target:**",
            reply_markup=build_target_keyboard(user_id, page),
            parse_mode="markdown",
        )
        await callback_query.answer()
        return

    # === TARGET VIEW ===
    if data.startswith("target_view_"):
        target_id = int(data.split("_")[-1])
        await callback_query.message.edit(
            f"📂 **Target {target_id}:**",
            reply_markup=build_target_detail_keyboard(user_id, target_id),
            parse_mode="markdown",
        )
        await callback_query.answer()
        return

    # === TARGET TOGGLE ===
    if data.startswith("target_toggle_"):
        target_id = int(data.split("_")[-1])
        target = TargetConfig.get(user_id, target_id)
        if target:
            target.enabled = not target.enabled
            target.save()
        await callback_query.message.edit(
            f"📂 **Target {target_id}:**",
            reply_markup=build_target_detail_keyboard(user_id, target_id),
            parse_mode="markdown",
        )
        await callback_query.answer()
        return

    # === TARGET ADD SOURCE ===
    if data.startswith("target_add_src_"):
        target_id = int(data.split("_")[-1])
        await callback_query.message.edit(
            f"➕ **Thêm nguồn vào Target {target_id}:**\n\n"
            "Gửi: `/addsource [source_id]`\n"
            "Ví dụ: `/addsource -100123456789`",
            parse_mode="markdown",
        )
        await callback_query.answer()
        return

    # === TARGET SET MEDIA ===
    if data.startswith("target_set_video_"):
        target_id = int(data.split("_")[-1])
        sources = SourceConfig.get_by_target(user_id, target_id)
        for src in sources:
            filter_cfg = FilterConfig.get(user_id, src.source_chat_id)
            filter_cfg.media_types = [MediaType.VIDEO]
            filter_cfg.save()
        await callback_query.answer("✅ Đã set all → Video")
        await callback_query.message.edit(
            f"📂 **Target {target_id}:**",
            reply_markup=build_target_detail_keyboard(user_id, target_id),
            parse_mode="markdown",
        )
        return

    if data.startswith("target_set_photo_"):
        target_id = int(data.split("_")[-1])
        sources = SourceConfig.get_by_target(user_id, target_id)
        for src in sources:
            filter_cfg = FilterConfig.get(user_id, src.source_chat_id)
            filter_cfg.media_types = [MediaType.PHOTO]
            filter_cfg.save()
        await callback_query.answer("✅ Đã set all → Ảnh")
        await callback_query.message.edit(
            f"📂 **Target {target_id}:**",
            reply_markup=build_target_detail_keyboard(user_id, target_id),
            parse_mode="markdown",
        )
        return

    # === TARGET DELETE ===
    if data.startswith("target_del_"):
        target_id = int(data.split("_")[-1])
        TargetConfig.delete(user_id, target_id)
        await callback_query.answer("✅ Đã xóa target")
        await callback_query.message.edit(
            "📂 **Danh sách Target:**",
            reply_markup=build_target_keyboard(user_id),
            parse_mode="markdown",
        )
        return

    # === TARGET CONFIG ===
    if data.startswith("target_config_"):
        target_id = int(data.split("_")[-1])
        target = TargetConfig.get(user_id, target_id)
        if target:
            target.enabled = not target.enabled
            target.save()
        await callback_query.message.edit(
            f"📂 **Target {target_id}:**",
            reply_markup=build_target_detail_keyboard(user_id, target_id),
            parse_mode="markdown",
        )
        await callback_query.answer()
        return

    # === SOURCE EDIT ===
    if data.startswith("src_edit_"):
        source_id = int(data.split("_")[-1])
        await callback_query.message.edit(
            f"⚙️ **Cấu hình nguồn {source_id}:**",
            reply_markup=build_filter_keyboard(user_id, source_id),
            parse_mode="markdown",
        )
        await callback_query.answer()
        return

    # === SOURCE DELETE ===
    if data.startswith("src_del_"):
        source_id = int(data.split("_")[-1])
        SourceConfig.delete(user_id, source_id)
        source = SourceConfig.get(user_id, source_id)
        if source:
            await callback_query.message.edit(
                f"📂 **Target {source.target_chat_id}:**",
                reply_markup=build_target_detail_keyboard(
                    user_id, source.target_chat_id
                ),
                parse_mode="markdown",
            )
        else:
            await callback_query.message.edit(
                "📂 **Danh sách Target:**",
                reply_markup=build_target_keyboard(user_id),
                parse_mode="markdown",
            )
        await callback_query.answer()
        return

    # === SOURCE TOGGLE (from filter) ===
    if data.startswith("filter_toggle_"):
        source_id = int(data.split("_")[-1])
        filter_cfg = FilterConfig.get(user_id, source_id)
        filter_cfg.enabled = not filter_cfg.enabled
        filter_cfg.save()
        await callback_query.message.edit(
            f"⚙️ **Cấu hình nguồn {source_id}:**",
            reply_markup=build_filter_keyboard(user_id, source_id),
            parse_mode="markdown",
        )
        await callback_query.answer()
        return

    # === MEDIA TOGGLE ===
    if data.startswith("media_toggle_") or data.startswith("media_all_"):
        parts = data.split("_")
        if parts[0] == "media" and parts[1] == "all":
            source_id = int(parts[-1])
            filter_cfg = FilterConfig.get(user_id, source_id)
            filter_cfg.media_types = [MediaType.ALL]
            filter_cfg.save()
            await callback_query.answer("✅ All media types")
        else:
            media_type = parts[2]
            source_id = int(parts[-1])
            filter_cfg = FilterConfig.get(user_id, source_id)

            media_enum = MediaType(media_type)
            if media_enum in filter_cfg.media_types:
                filter_cfg.media_types.remove(media_enum)
            else:
                if MediaType.ALL in filter_cfg.media_types:
                    filter_cfg.media_types = [media_enum]
                else:
                    filter_cfg.media_types.append(media_enum)

            if not filter_cfg.media_types:
                filter_cfg.media_types = [MediaType.ALL]

            filter_cfg.save()

        await callback_query.message.edit(
            f"⚙️ **Cấu hình nguồn {source_id}:**",
            reply_markup=build_filter_keyboard(user_id, source_id),
            parse_mode="markdown",
        )
        await callback_query.answer()
        return

    # === DURATION PRESETS ===
    if data.startswith("dur_preset_"):
        parts = data.split("_")
        duration = int(parts[2])
        source_id = int(parts[-1])

        filter_cfg = FilterConfig.get(user_id, source_id)
        filter_cfg.min_duration = duration
        filter_cfg.save()

        await callback_query.answer(f"✅ Min: {duration}s")
        await callback_query.message.edit(
            f"⚙️ **Cấu hình nguồn {source_id}:**",
            reply_markup=build_filter_keyboard(user_id, source_id),
            parse_mode="markdown",
        )
        return

    if data.startswith("dur_clear_"):
        source_id = int(data.split("_")[-1])
        filter_cfg = FilterConfig.get(user_id, source_id)
        filter_cfg.min_duration = 0
        filter_cfg.max_duration = None
        filter_cfg.save()

        await callback_query.answer("✅ Đã bỏ limit")
        await callback_query.message.edit(
            f"⚙️ **Cấu hình nguồn {source_id}:**",
            reply_markup=build_filter_keyboard(user_id, source_id),
            parse_mode="markdown",
        )
        return

    # === ADD TARGET ===
    if data == "target_add":
        await callback_query.message.edit(
            "➕ **Thêm Target mới:**\n\n"
            "Gửi: `/addtarget [target_id] [tên (tùy chọn)]`\n\n"
            "Ví dụ:\n"
            "`/addtarget -100123456789`\n"
            "`/addtarget -100123456789 My Channel`",
            parse_mode="markdown",
        )
        await callback_query.answer()
        return

    # === MAIN MENU QUICK FILTERS ===
    if data == "main_video":
        sources = SourceConfig.get_all(user_id)
        for src in sources:
            filter_cfg = FilterConfig.get(user_id, src.source_chat_id)
            filter_cfg.media_types = [MediaType.VIDEO]
            filter_cfg.save()
        await callback_query.answer("✅ All → Video")
        await callback_query.message.edit(
            "⚙️ **Menu cấu hình:**",
            reply_markup=build_main_menu_keyboard(),
            parse_mode="markdown",
        )
        return

    if data == "main_photo":
        sources = SourceConfig.get_all(user_id)
        for src in sources:
            filter_cfg = FilterConfig.get(user_id, src.source_chat_id)
            filter_cfg.media_types = [MediaType.PHOTO]
            filter_cfg.save()
        await callback_query.answer("✅ All → Ảnh")
        await callback_query.message.edit(
            "⚙️ **Menu cấu hình:**",
            reply_markup=build_main_menu_keyboard(),
            parse_mode="markdown",
        )
        return

    if data == "main_doc":
        sources = SourceConfig.get_all(user_id)
        for src in sources:
            filter_cfg = FilterConfig.get(user_id, src.source_chat_id)
            filter_cfg.media_types = [MediaType.DOCUMENT]
            filter_cfg.save()
        await callback_query.answer("✅ All → Document")
        await callback_query.message.edit(
            "⚙️ **Menu cấu hình:**",
            reply_markup=build_main_menu_keyboard(),
            parse_mode="markdown",
        )
        return

    if data == "main_duration":
        await callback_query.message.edit(
            "⏱ **Cấu hình Duration mặc định:**\n\n"
            "Gửi: `/default [min]_[max]`\n"
            "Ví dụ: `/default 60_300`",
            parse_mode="markdown",
        )
        await callback_query.answer()
        return

    if data == "main_realtime":
        await callback_query.message.edit(
            "⚡ **Realtime Forward**",
            reply_markup=build_realtime_keyboard(user_id),
            parse_mode="markdown",
        )
        await callback_query.answer()
        return

    # === REALTIME CONTROLS ===
    if data == "realtime_on":
        from bot import realtime_running, users

        user_data = users.find_one({"user_id": user_id})

        if not user_data or not user_data.get("session_string"):
            await callback_query.answer("❗ Cần /login trước!", show_alert=True)
            return

        realtime_running[user_id] = True
        await callback_query.answer("✅ Realtime đã bật!")
        await callback_query.message.edit(
            "⚡ **Realtime Forward**\n\n✅ Đang chạy\n\n/realtime off để tắt",
            reply_markup=build_realtime_keyboard(user_id),
            parse_mode="markdown",
        )

        import asyncio
        from bot import start_realtime_forward

        asyncio.create_task(start_realtime_forward(user_id))
        return

    if data == "realtime_off":
        from bot import realtime_running

        realtime_running[user_id] = False
        await callback_query.answer("❎ Realtime đã tắt")
        await callback_query.message.edit(
            "⚡ **Realtime Forward**\n\n❌ Đã dừng\n\n/realtime on để bật",
            reply_markup=build_realtime_keyboard(user_id),
            parse_mode="markdown",
        )
        return

    await callback_query.answer()
