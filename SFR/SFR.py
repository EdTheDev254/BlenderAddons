bl_info = {
    "name": "Selective Frame Renderer - SFR",
    "author": "Edwin, Gemini 2.5 Pro and ChatGPT",
    "version": (3, 5),
    "blender": (4, 0, 0),
    "location": "Properties > Output",
    "description": "Correctly saves all frames and updates the default Render Result view. Adds Render All button.",
    "category": "Render",
}

import bpy
import os

# ---------- helpers ----------
def get_file_extension(scene):
    img_format = scene.render.image_settings.file_format
    ext_map = {
        'BMP': 'bmp', 'IRIS': 'iris', 'PNG': 'png', 'JPEG': 'jpg',
        'JPEG2000': 'jp2', 'TARGA': 'tga', 'TARGA_RAW': 'tga',
        'CINEON': 'cin', 'DPX': 'dpx', 'TIFF': 'tif',
        'OPEN_EXR_MULTILAYER': 'exr', 'OPEN_EXR': 'exr', 'HDR': 'hdr'
    }
    return ext_map.get(img_format, 'png')

def safe_status_text_set(context, text):
    try:
        context.workspace.status_text_set(text=text)
    except Exception:
        # ignore if workspace or context is not suitable (e.g., background mode)
        pass

def safe_cursor_set(window, cursor_value):
    if not window:
        return
    try:
        window.cursor_set(cursor_value)
    except Exception:
        try:
            window.cursor_modal_set(cursor_value)
        except Exception:
            pass

# ---------- properties & UI ----------
class ExcludeFrameRange(bpy.types.PropertyGroup):
    start: bpy.props.IntProperty(name="Start", default=1, min=0)
    end: bpy.props.IntProperty(name="End", default=1, min=0)

class FRAME_UL_exclude_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.prop(item, "start", text="Start")
        layout.prop(item, "end", text="End")

class FRAME_OT_add_range(bpy.types.Operator):
    bl_idname = "frame.exclude_add"
    bl_label = "Add Frame Range"
    def execute(self, context):
        context.scene.exclude_frame_ranges.add()
        return {'FINISHED'}

class FRAME_OT_remove_range(bpy.types.Operator):
    bl_idname = "frame.exclude_remove"
    bl_label = "Remove Selected Range"
    def execute(self, context):
        idx = context.scene.exclude_range_index
        if 0 <= idx < len(context.scene.exclude_frame_ranges):
            context.scene.exclude_frame_ranges.remove(idx)
            context.scene.exclude_range_index = max(0, idx - 1)
        return {'FINISHED'}

# ---------- Render (Filtered) operator (improved) ----------
class FRAME_OT_render_filtered(bpy.types.Operator):
    bl_idname = "frame.render_filtered"
    bl_label = "Render (Filtered)"
    bl_description = "Render frames excluding specified ranges; live timeline view."

    _timer = None
    frames_to_render = []
    total_frames = 0
    current_frame_index = 0

    original_filepath = ""
    extension = ""

    def execute(self, context):
        scene = context.scene
        self.original_filepath = scene.render.filepath

        if not self.original_filepath or self.original_filepath.strip() == "":
            self.report({'ERROR'}, "Output path is empty.")
            return {'CANCELLED'}
        if self.original_filepath.endswith(os.sep) or self.original_filepath.endswith("/"):
            self.report({'ERROR'}, "Output path is missing a filename prefix (e.g., 'render_').")
            return {'CANCELLED'}

        self.extension = get_file_extension(scene)

        start = scene.frame_start
        end = scene.frame_end
        excluded = set()

        self.frames_to_render.clear()
        for r in scene.exclude_frame_ranges:
            if r.start <= r.end:
                excluded.update(range(r.start, r.end + 1))

        for frame in range(start, end + 1):
            if frame not in excluded:
                self.frames_to_render.append(frame)

        if not self.frames_to_render:
            self.report({'WARNING'}, "No frames to render after exclusions.")
            return {'CANCELLED'}

        self.total_frames = len(self.frames_to_render)
        self.current_frame_index = 0

        wm = context.window_manager
        wm.progress_begin(0, self.total_frames)
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        # try set wait cursor
        safe_cursor_set(context.window, 'WAIT')

        self.report({'INFO'}, "Live View Started. View updates in the 'Render Result' image.")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            if self.current_frame_index >= self.total_frames:
                # finished
                self.finish(context)
                self.report({'INFO'}, "Rendering completed successfully.")
                return {'FINISHED'}

            frame = self.frames_to_render[self.current_frame_index]
            context.scene.frame_set(frame)

            final_path = f"{self.original_filepath}{frame:04d}.{self.extension}"
            context.scene.render.filepath = final_path

            progress_text = f"Rendering Frame {frame} -> {os.path.basename(final_path)}"
            print(progress_text)
            safe_status_text_set(context, progress_text)
            try:
                bpy.ops.render.render(write_still=True)
                # attempt to refresh the default Render Result image
                rr = bpy.data.images.get("Render Result")
                if rr:
                    try:
                        rr.reload()
                    except Exception:
                        pass
            except Exception as e:
                self.report({'ERROR'}, f"Failed at frame {frame}: {e}")
                self.cancel(context)
                return {'CANCELLED'}

            self.current_frame_index += 1
            context.window_manager.progress_update(self.current_frame_index)

        return {'RUNNING_MODAL'}

    def finish(self, context):
        context.scene.render.filepath = self.original_filepath
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
        wm.progress_end()
        safe_status_text_set(context, "")
        safe_cursor_set(context.window, 'DEFAULT')
        print("--- Selective Renderer Finished ---")

    def cancel(self, context):
        # ensure restore state
        context.scene.render.filepath = self.original_filepath
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
        wm.progress_end()
        safe_status_text_set(context, "")
        safe_cursor_set(context.window, 'DEFAULT')
        print("--- Selective Renderer Cancelled ---")

# ---------- Render All operator (new) ----------
class FRAME_OT_render_all(bpy.types.Operator):
    bl_idname = "frame.render_all"
    bl_label = "Render (All)"
    bl_description = "Render all frames from start to end; live timeline view."

    _timer = None
    frames_to_render = []
    total_frames = 0
    current_frame_index = 0

    original_filepath = ""
    extension = ""

    def execute(self, context):
        scene = context.scene
        self.original_filepath = scene.render.filepath

        if not self.original_filepath or self.original_filepath.strip() == "":
            self.report({'ERROR'}, "Output path is empty.")
            return {'CANCELLED'}
        if self.original_filepath.endswith(os.sep) or self.original_filepath.endswith("/"):
            self.report({'ERROR'}, "Output path is missing a filename prefix (e.g., 'render_').")
            return {'CANCELLED'}

        self.extension = get_file_extension(scene)

        start = scene.frame_start
        end = scene.frame_end

        self.frames_to_render = list(range(start, end + 1))

        if not self.frames_to_render:
            self.report({'WARNING'}, "No frames to render.")
            return {'CANCELLED'}

        self.total_frames = len(self.frames_to_render)
        self.current_frame_index = 0

        wm = context.window_manager
        wm.progress_begin(0, self.total_frames)
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        safe_cursor_set(context.window, 'WAIT')

        self.report({'INFO'}, "Live View Started. View updates in the 'Render Result' image.")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            if self.current_frame_index >= self.total_frames:
                self.finish(context)
                self.report({'INFO'}, "Rendering completed successfully.")
                return {'FINISHED'}

            frame = self.frames_to_render[self.current_frame_index]
            context.scene.frame_set(frame)

            final_path = f"{self.original_filepath}{frame:04d}.{self.extension}"
            context.scene.render.filepath = final_path

            progress_text = f"Rendering Frame {frame} -> {os.path.basename(final_path)}"
            print(progress_text)
            safe_status_text_set(context, progress_text)
            try:
                bpy.ops.render.render(write_still=True)
                rr = bpy.data.images.get("Render Result")
                if rr:
                    try:
                        rr.reload()
                    except Exception:
                        pass
            except Exception as e:
                self.report({'ERROR'}, f"Failed at frame {frame}: {e}")
                self.cancel(context)
                return {'CANCELLED'}

            self.current_frame_index += 1
            context.window_manager.progress_update(self.current_frame_index)

        return {'RUNNING_MODAL'}

    def finish(self, context):
        context.scene.render.filepath = self.original_filepath
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
        wm.progress_end()
        safe_status_text_set(context, "")
        safe_cursor_set(context.window, 'DEFAULT')
        print("--- Full Renderer Finished ---")

    def cancel(self, context):
        context.scene.render.filepath = self.original_filepath
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
        wm.progress_end()
        safe_status_text_set(context, "")
        safe_cursor_set(context.window, 'DEFAULT')
        print("--- Full Renderer Cancelled ---")

# ---------- PANEL ----------
class FRAME_PT_exclude_panel(bpy.types.Panel):
    bl_label = "Selective Frame Renderer"
    bl_idname = "FRAME_PT_exclude_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "output"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="Exclude Frame Ranges:")
        row = layout.row()
        row.template_list("FRAME_UL_exclude_list", "", scene, "exclude_frame_ranges", scene, "exclude_range_index")
        col = row.column(align=True)
        col.operator("frame.exclude_add", icon='ADD', text="")
        col.operator("frame.exclude_remove", icon='REMOVE', text="")
        layout.separator()
        # two buttons - filtered and all
        row = layout.row(align=True)
        row.operator("frame.render_filtered", icon='RENDER_ANIMATION')
        row.operator("frame.render_all", icon='RENDER_ANIMATION')

# ---------- registration ----------
classes = (
    ExcludeFrameRange,
    FRAME_UL_exclude_list,
    FRAME_OT_add_range,
    FRAME_OT_remove_range,
    FRAME_OT_render_filtered,
    FRAME_OT_render_all,
    FRAME_PT_exclude_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.exclude_frame_ranges = bpy.props.CollectionProperty(type=ExcludeFrameRange)
    bpy.types.Scene.exclude_range_index = bpy.props.IntProperty()

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.exclude_frame_ranges
    del bpy.types.Scene.exclude_range_index

if __name__ == "__main__":
    register()
