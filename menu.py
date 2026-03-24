from pyrogram import types
from filters import FilterConfig, MediaType, SourceConfig, TargetConfig

PAGE_SIZE = 5


def get_media_icon(media_types: list) -> str:
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
    if MediaType.VOICE in media_types:
        return "🎤"
    if MediaType.VIDEO_NOTE in media_types:
        return "⭕"
    if MediaType.STICKER in media_types:
        return "😎"
    if MediaType.ANIMATION in media_types:
        return "🎬"
    return "📝"


def build_main_menu_keyboard():
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


def build_target_keyboard(user_id: int, page: int = 0):
    targets = TargetConfig.get_all(user_id)
    total_pages = max(1, (len(targets) + PAGE_SIZE - 1) // PAGE_SIZE)

    keyboard = []
    keyboard.append(
        [types.InlineKeyboardButton("📂 DANH SÁCH TARGET", callback_data="noop")]
    )

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE

    for target in targets[start:end]:
        sources = target.get_sources()
        status = "🟢" if target.enabled else "🔴"
        keyboard.append(
            [
                types.InlineKeyboardButton(
                    f"{status} {target.name} ({len(sources)} nguồn)",
                    callback_data=f"target_view_{target.target_chat_id}",
                )
            ]
        )

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

    keyboard.append(
        [types.InlineKeyboardButton("➕ Thêm Target mới", callback_data="target_add")]
    )
    keyboard.append(
        [types.InlineKeyboardButton("🔙 Quay lại", callback_data="menu_main")]
    )
    return types.InlineKeyboardMarkup(keyboard)


def build_target_detail_keyboard(user_id: int, target_chat_id: int):
    target = TargetConfig.get(user_id, target_chat_id)
    if not target:
        return build_target_keyboard(user_id)

    sources = target.get_sources()
    keyboard = []
    status = "🟢" if target.enabled else "🔴"
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"{status} 📂 {target.name}",
                callback_data=f"target_toggle_{target_chat_id}",
            )
        ]
    )
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
                "🎯 Set all → Video", callback_data=f"target_set_video_{target_chat_id}"
            )
        ]
    )
    keyboard.append(
        [
            types.InlineKeyboardButton(
                "📷 Set all → Ảnh", callback_data=f"target_set_photo_{target_chat_id}"
            )
        ]
    )
    keyboard.append(
        [types.InlineKeyboardButton("🔙 Quay lại", callback_data="menu_targets")]
    )
    return types.InlineKeyboardMarkup(keyboard)


def build_filter_keyboard(user_id: int, source_chat_id: int, page: int = 0):
    filter_config = FilterConfig.get(user_id, source_chat_id)
    source_config = SourceConfig.get(user_id, source_chat_id)
    if not source_config:
        return build_target_keyboard(user_id)

    if page == 0:
        return _build_filter_page_media(user_id, source_chat_id, filter_config)
    elif page == 1:
        return _build_filter_page_forward(user_id, source_chat_id, filter_config)
    elif page == 2:
        return _build_filter_page_content(user_id, source_chat_id, filter_config)
    else:
        return _build_filter_page_media(user_id, source_chat_id, filter_config)


def _build_filter_page_media(user_id, source_chat_id, filter_config):
    keyboard = []
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"📨 MEDIA - {source_chat_id}", callback_data="noop"
            )
        ]
    )
    keyboard.append(
        [
            types.InlineKeyboardButton(
                "📨 Media", callback_data=f"filter_page_0_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "📤 Forward", callback_data=f"filter_page_1_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "📝 Content", callback_data=f"filter_page_2_{source_chat_id}"
            ),
        ]
    )

    status = "🔴 TẮT" if filter_config.enabled else "🟢 BẬT"
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"▶️ {status}", callback_data=f"filter_toggle_{source_chat_id}"
            )
        ]
    )
    keyboard.append([types.InlineKeyboardButton("Chọn loại:", callback_data="noop")])

    media_options = [
        (MediaType.VIDEO, "📹 Video"),
        (MediaType.PHOTO, "📷 Ảnh"),
        (MediaType.DOCUMENT, "📄 Tài liệu"),
        (MediaType.AUDIO, "🔊 Audio"),
        (MediaType.VOICE, "🎤 Voice"),
        (MediaType.VIDEO_NOTE, "⭕ Video Note"),
        (MediaType.STICKER, "😎 Sticker"),
        (MediaType.ANIMATION, "🎬 Animation"),
        (MediaType.TEXT, "📝 Text"),
    ]

    row = []
    for media, label in media_options:
        is_selected = (
            media in filter_config.media_types
            or MediaType.ALL in filter_config.media_types
        )
        icon = "✅" if is_selected else "⬜"
        row.append(
            types.InlineKeyboardButton(
                f"{icon} {label}",
                callback_data=f"media_toggle_{media.value}_{source_chat_id}",
            )
        )
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    all_selected = MediaType.ALL in filter_config.media_types
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"{'✅' if all_selected else '⬜'} Tất cả",
                callback_data=f"media_all_{source_chat_id}",
            )
        ]
    )

    keyboard.append([types.InlineKeyboardButton("⏱ THỜI LƯỢNG", callback_data="noop")])
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
    keyboard.append(
        [
            types.InlineKeyboardButton(
                "1m+", callback_data=f"dur_preset_60_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "3m+", callback_data=f"dur_preset_180_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "5m+", callback_data=f"dur_preset_300_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "Clear", callback_data=f"dur_clear_{source_chat_id}"
            ),
        ]
    )

    keyboard.append(
        [
            types.InlineKeyboardButton(
                "🔙 Quay lại",
                callback_data=f"target_view_{SourceConfig.get(user_id, source_chat_id).target_chat_id}",
            )
        ]
    )
    return types.InlineKeyboardMarkup(keyboard)


def _build_filter_page_forward(user_id, source_chat_id, filter_config):
    keyboard = []
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"📤 FORWARD - {source_chat_id}", callback_data="noop"
            )
        ]
    )
    keyboard.append(
        [
            types.InlineKeyboardButton(
                "📨 Media", callback_data=f"filter_page_0_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "📤 Forward", callback_data=f"filter_page_1_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "📝 Content", callback_data=f"filter_page_2_{source_chat_id}"
            ),
        ]
    )

    keyboard.append(
        [types.InlineKeyboardButton("Tùy chọn copy/forward:", callback_data="noop")]
    )
    cap_icon = "✅" if filter_config.remove_caption else "⬜"
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"{cap_icon} Xóa caption", callback_data=f"opt_cap_{source_chat_id}"
            )
        ]
    )

    fwd_icon = "✅" if filter_config.remove_forward_header else "⬜"
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"{fwd_icon} Xóa tên nguồn", callback_data=f"opt_fwd_{source_chat_id}"
            )
        ]
    )

    keyboard.append(
        [types.InlineKeyboardButton("📦 KÍCH THƯỚC FILE", callback_data="noop")]
    )
    min_size = filter_config.min_file_size or 0
    max_size = filter_config.max_file_size
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"Min: {min_size / 1024 / 1024:.1f}MB",
                callback_data=f"size_min_{source_chat_id}",
            ),
            types.InlineKeyboardButton(
                f"Max: {max_size / 1024 / 1024:.1f}MB" if max_size else "Max: ∞",
                callback_data=f"size_max_{source_chat_id}",
            ),
        ]
    )
    keyboard.append(
        [
            types.InlineKeyboardButton(
                "5MB+", callback_data=f"size_5m_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "10MB+", callback_data=f"size_10m_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "20MB+", callback_data=f"size_20m_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "Clear", callback_data=f"size_clear_{source_chat_id}"
            ),
        ]
    )

    keyboard.append(
        [
            types.InlineKeyboardButton(
                "🔙 Quay lại",
                callback_data=f"target_view_{SourceConfig.get(user_id, source_chat_id).target_chat_id}",
            )
        ]
    )
    return types.InlineKeyboardMarkup(keyboard)


def _build_filter_page_content(user_id, source_chat_id, filter_config):
    keyboard = []
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"📝 CONTENT - {source_chat_id}", callback_data="noop"
            )
        ]
    )
    keyboard.append(
        [
            types.InlineKeyboardButton(
                "📨 Media", callback_data=f"filter_page_0_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "📤 Forward", callback_data=f"filter_page_1_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "📝 Content", callback_data=f"filter_page_2_{source_chat_id}"
            ),
        ]
    )

    keyboard.append([types.InlineKeyboardButton("Lọc nội dung:", callback_data="noop")])
    req_cap_icon = "✅" if filter_config.require_caption else "⬜"
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"{req_cap_icon} Bắt buộc có caption",
                callback_data=f"req_cap_{source_chat_id}",
            )
        ]
    )

    req_tag_icon = "✅" if filter_config.require_hashtags else "⬜"
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"{req_tag_icon} Bắt buộc có #hashtag",
                callback_data=f"req_tag_{source_chat_id}",
            )
        ]
    )

    keyboard.append(
        [types.InlineKeyboardButton("🚫 TỪ KHÓA BLOCK:", callback_data="noop")]
    )
    block_text = (
        ", ".join(filter_config.block_list) if filter_config.block_list else "(trống)"
    )
    keyboard.append(
        [
            types.InlineKeyboardButton(
                f"📝 {block_text[:30]}{'...' if len(block_text) > 30 else ''}",
                callback_data=f"block_edit_{source_chat_id}",
            )
        ]
    )
    keyboard.append(
        [
            types.InlineKeyboardButton(
                "➕ Thêm từ", callback_data=f"block_add_{source_chat_id}"
            ),
            types.InlineKeyboardButton(
                "🗑️ Xóa all", callback_data=f"block_clear_{source_chat_id}"
            ),
        ]
    )

    keyboard.append(
        [
            types.InlineKeyboardButton(
                "🔙 Quay lại",
                callback_data=f"target_view_{SourceConfig.get(user_id, source_chat_id).target_chat_id}",
            )
        ]
    )
    return types.InlineKeyboardMarkup(keyboard)


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


async def handle_callback(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id

    if data == "noop":
        await callback_query.answer()
        return

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
• Nguồn: **{len(sources)}** (🟢 {enabled_sources})
• Realtime: **{rt_status}**

📹 Video: {media_stats.get("video", 0)}
📷 Ảnh: {media_stats.get("photo", 0)}
📄 Doc: {media_stats.get("document", 0)}"""
        await callback_query.message.edit(
            text, reply_markup=build_stats_keyboard(user_id), parse_mode="markdown"
        )
        await callback_query.answer()
        return

    # Filter page navigation
    if data.startswith("filter_page_"):
        parts = data.split("_")
        page = int(parts[2])
        source_id = int(parts[3])
        await callback_query.message.edit(
            "⚙️",
            reply_markup=build_filter_keyboard(user_id, source_id, page),
            parse_mode="markdown",
        )
        await callback_query.answer()
        return

    # Target operations
    if data.startswith("target_page_"):
        page = int(data.split("_")[-1])
        await callback_query.message.edit(
            "📂 **Danh sách Target:**",
            reply_markup=build_target_keyboard(user_id, page),
            parse_mode="markdown",
        )
        return

    if data.startswith("target_view_"):
        target_id = int(data.split("_")[-1])
        await callback_query.message.edit(
            f"📂 **Target {target_id}:**",
            reply_markup=build_target_detail_keyboard(user_id, target_id),
            parse_mode="markdown",
        )
        return

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
        return

    if data.startswith("target_add_src_"):
        target_id = int(data.split("_")[-1])
        await callback_query.message.edit(
            f"➕ **Thêm nguồn vào Target {target_id}:**\n\nGửi: `/addsource [source_id]`",
            parse_mode="markdown",
        )
        return

    if data.startswith("target_set_video_"):
        target_id = int(data.split("_")[-1])
        sources = SourceConfig.get_by_target(user_id, target_id)
        for src in sources:
            filter_cfg = FilterConfig.get(user_id, src.source_chat_id)
            filter_cfg.media_types = [MediaType.VIDEO]
            filter_cfg.save()
        await callback_query.answer("✅ All → Video")
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
        await callback_query.answer("✅ All → Ảnh")
        await callback_query.message.edit(
            f"📂 **Target {target_id}:**",
            reply_markup=build_target_detail_keyboard(user_id, target_id),
            parse_mode="markdown",
        )
        return

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

    # Source operations
    if data.startswith("src_edit_"):
        source_id = int(data.split("_")[-1])
        await callback_query.message.edit(
            f"⚙️ **Cấu hình {source_id}:**",
            reply_markup=build_filter_keyboard(user_id, source_id, 0),
            parse_mode="markdown",
        )
        return

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
        return

    # Filter toggle
    if data.startswith("filter_toggle_"):
        source_id = int(data.split("_")[-1])
        filter_cfg = FilterConfig.get(user_id, source_id)
        filter_cfg.enabled = not filter_cfg.enabled
        filter_cfg.save()
        await callback_query.message.edit(
            f"⚙️ **Cấu hình {source_id}:**",
            reply_markup=build_filter_keyboard(user_id, source_id, 0),
            parse_mode="markdown",
        )
        return

    # Media toggle
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
            f"⚙️ **Cấu hình {source_id}:**",
            reply_markup=build_filter_keyboard(user_id, source_id, 0),
            parse_mode="markdown",
        )
        return

    # Duration presets
    if data.startswith("dur_preset_"):
        parts = data.split("_")
        duration = int(parts[2])
        source_id = int(parts[-1])
        filter_cfg = FilterConfig.get(user_id, source_id)
        filter_cfg.min_duration = duration
        filter_cfg.save()
        await callback_query.answer(f"✅ Min: {duration}s")
        await callback_query.message.edit(
            f"⚙️ **Cấu hình {source_id}:**",
            reply_markup=build_filter_keyboard(user_id, source_id, 0),
            parse_mode="markdown",
        )
        return

    if data.startswith("dur_clear_"):
        source_id = int(data.split("_")[-1])
        filter_cfg = FilterConfig.get(user_id, source_id)
        filter_cfg.min_duration = 0
        filter_cfg.max_duration = None
        filter_cfg.save()
        await callback_query.answer("✅ Đã clear")
        await callback_query.message.edit(
            f"⚙️ **Cấu hình {source_id}:**",
            reply_markup=build_filter_keyboard(user_id, source_id, 0),
            parse_mode="markdown",
        )
        return

    # Forward options
    if data.startswith("opt_cap_"):
        source_id = int(data.split("_")[-1])
        filter_cfg = FilterConfig.get(user_id, source_id)
        filter_cfg.remove_caption = not filter_cfg.remove_caption
        filter_cfg.save()
        await callback_query.message.edit(
            f"⚙️ **Cấu hình {source_id}:**",
            reply_markup=build_filter_keyboard(user_id, source_id, 1),
            parse_mode="markdown",
        )
        return

    if data.startswith("opt_fwd_"):
        source_id = int(data.split("_")[-1])
        filter_cfg = FilterConfig.get(user_id, source_id)
        filter_cfg.remove_forward_header = not filter_cfg.remove_forward_header
        filter_cfg.save()
        await callback_query.message.edit(
            f"⚙️ **Cấu hình {source_id}:**",
            reply_markup=build_filter_keyboard(user_id, source_id, 1),
            parse_mode="markdown",
        )
        return

    # File size
    if data.startswith("size_"):
        parts = data.split("_")
        size_type = parts[1]
        source_id = int(parts[-1])
        filter_cfg = FilterConfig.get(user_id, source_id)
        if size_type == "5m":
            filter_cfg.min_file_size = 5 * 1024 * 1024
        elif size_type == "10m":
            filter_cfg.min_file_size = 10 * 1024 * 1024
        elif size_type == "20m":
            filter_cfg.min_file_size = 20 * 1024 * 1024
        elif size_type == "clear":
            filter_cfg.min_file_size = 0
            filter_cfg.max_file_size = None
        filter_cfg.save()
        await callback_query.answer("✅ Size updated")
        await callback_query.message.edit(
            f"⚙️ **Cấu hình {source_id}:**",
            reply_markup=build_filter_keyboard(user_id, source_id, 1),
            parse_mode="markdown",
        )
        return

    # Content options
    if data.startswith("req_cap_"):
        source_id = int(data.split("_")[-1])
        filter_cfg = FilterConfig.get(user_id, source_id)
        filter_cfg.require_caption = not filter_cfg.require_caption
        filter_cfg.save()
        await callback_query.message.edit(
            f"⚙️ **Cấu hình {source_id}:**",
            reply_markup=build_filter_keyboard(user_id, source_id, 2),
            parse_mode="markdown",
        )
        return

    if data.startswith("req_tag_"):
        source_id = int(data.split("_")[-1])
        filter_cfg = FilterConfig.get(user_id, source_id)
        filter_cfg.require_hashtags = not filter_cfg.require_hashtags
        filter_cfg.save()
        await callback_query.message.edit(
            f"⚙️ **Cấu hình {source_id}:**",
            reply_markup=build_filter_keyboard(user_id, source_id, 2),
            parse_mode="markdown",
        )
        return

    if data.startswith("block_clear_"):
        source_id = int(data.split("_")[-1])
        filter_cfg = FilterConfig.get(user_id, source_id)
        filter_cfg.block_list = []
        filter_cfg.save()
        await callback_query.answer("✅ Đã clear")
        await callback_query.message.edit(
            f"⚙️ **Cấu hình {source_id}:**",
            reply_markup=build_filter_keyboard(user_id, source_id, 2),
            parse_mode="markdown",
        )
        return

    if data == "target_add":
        await callback_query.message.edit(
            "➕ **Thêm Target mới:**\n\nGửi: `/addtarget [target_id] [tên]`",
            parse_mode="markdown",
        )
        return

    # Main menu quick filters
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
            "⏱ **Cấu hình Duration mặc định:**\n\nGửi: `/default [min]_[max]`",
            parse_mode="markdown",
        )
        return

    if data == "main_realtime":
        await callback_query.message.edit(
            "⚡ **Realtime Forward**",
            reply_markup=build_realtime_keyboard(user_id),
            parse_mode="markdown",
        )
        return

    if data == "realtime_on":
        from bot import realtime_running, users

        user_data = users.find_one({"user_id": user_id})
        if not user_data or not user_data.get("session_string"):
            await callback_query.answer("❗ Cần /login trước!", show_alert=True)
            return
        realtime_running[user_id] = True
        await callback_query.answer("✅ Realtime đã bật!")
        await callback_query.message.edit(
            "⚡ **Realtime Forward**\n\n✅ Đang chạy",
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
            "⚡ **Realtime Forward**\n\n❌ Đã dừng",
            reply_markup=build_realtime_keyboard(user_id),
            parse_mode="markdown",
        )
        return

    await callback_query.answer()
