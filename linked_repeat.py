# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
#  Author: Dealga McArdle (@zeffii)
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Primitive Repeat",
    "author": "Dealga McArdle",
    "version": (0, 0, 2),
    "blender": (2, 7, 4),
    "location": "3dview, key combo",
    "description": "Places items at N even/random intervals between 2 linked dups.",
    "wiki_url": "",
    "tracker_url": "",
    "keywords": ("duplicate", "repeat", "random", "spread"),
    "category": "Mesh"}

import time

import bpy
import random
from mathutils import Vector


Scene = bpy.types.Scene


def obj_id(caller):
    return str(hash(caller) ^ hash(time.monotonic()))


def remove_obj(obj):
    scene = bpy.context.scene
    objs = bpy.data.objects
    me = obj.data
    scene.objects.unlink(obj)
    objs.remove(obj)


def remove_excess_linked(idx, current_id):
    for o in bpy.data.objects:
        if not o.get('SKETCHPAD_ID'):
            continue
        if not (o['SKETCHPAD_ID'] == current_id):
            continue
        if o['SKETCHPAD_IDX'] > idx:
            remove_obj(o)


def get_objs_and_meshnames():
    sel_objs = bpy.context.selected_objects
    objs = [o for o in sel_objs if o.type == 'MESH']
    mesh_names = [o.data.name for o in objs]
    return objs, mesh_names


class ModalPrimitiveRepeat(bpy.types.Operator):

    bl_idname = "view3d.linked_primitive_repeat"
    bl_label = "SP style primitive repeat"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'REGISTER', 'UNDO'}

    SP_NUM_ITEMS = bpy.props.IntProperty(default=3, min=3)
    SP_OPERATOR_RUNNING = bpy.props.BoolProperty(default=False)
    SP_OBJ_IDENTIFIER = bpy.props.StringProperty()
    SP_RANDOM_SEED = bpy.props.IntProperty()

    def add_duplicate_linked(self, idx, named_object, named_mesh, loc):
        meshes = bpy.data.meshes
        scn = bpy.context.scene
        objects = bpy.data.objects
        me = meshes.get(named_mesh)
        ID = self.SP_OBJ_IDENTIFIER

        # ADD OR REUSE and update location..
        def find(ID, idx):
            for obj in objects:
                if obj.type == 'MESH':
                    rval = obj.get('SKETCHPAD_ID')
                    if rval == ID:
                        if obj.get('SKETCHPAD_IDX') == idx:
                            return obj
        result = find(ID, idx)
        if result:
            obj = result
        else:
            obj = objects.new(named_object, me)
            scn.objects.link(obj)
            obj['SKETCHPAD_ID'] = ID
            obj['SKETCHPAD_IDX'] = idx
        obj.location = loc

    def add_between_duplicate_linked(self, num_items=3, rand=False):
        if num_items < 3:
            return

        num_items -= 2
        rate = 1 / (num_items + 1)

        # two objects, both reference the same mesh?
        objs, mesh_names = get_objs_and_meshnames()
        if not (len(mesh_names) == 2) or not (len(set(mesh_names)) == 1):
            return

        loc1, loc2 = objs[0].location, objs[1].location
        named_mesh = mesh_names[0]

        obj_names = [o.name for o in objs]
        pick_name = sorted(obj_names)[0]

        if rand >= 1:
            random.seed(rand)
            rnd_rates = [random.random() for r in range(num_items)]
            for i, r in enumerate(rnd_rates, 1):
                loc = loc1.lerp(loc2, r)
                self.add_duplicate_linked(i, pick_name, named_mesh, loc)

        else:
            for i in range(1, num_items + 1):
                loc = loc1.lerp(loc2, i * rate)
                self.add_duplicate_linked(i, pick_name, named_mesh, loc)

    def handle_user_interaction(self, context, event):
        scn = context.scene
        n = event.type
        handled = False

        if not event.ctrl:
            if n in {'LEFT_BRACKET', 'RIGHT_BRACKET'}:
                self.SP_NUM_ITEMS += (1 if (n == 'RIGHT_BRACKET') else -1)
                handled = True
        else:
            if n in {'DOWN_ARROW', 'UP_ARROW'}:
                self.SP_RANDOM_SEED += (1 if (n == 'UP_ARROW') else -1)
                self.SP_RANDOM_SEED = max(self.SP_RANDOM_SEED, 0)
                handled = True

        if handled:
            current_id = self.SP_OBJ_IDENTIFIER
            num_items = self.SP_NUM_ITEMS
            seed = self.SP_RANDOM_SEED
            self.add_between_duplicate_linked(num_items=num_items, rand=seed)
            remove_excess_linked(num_items - 2, current_id)

        return handled

    def modal(self, context, event):
        # context.area.tag_redraw()
        scn = context.scene
        n = event.type

        if n in {'RIGHTMOUSE', 'ESC'}:
            obj = context.active_object
            self.SP_OPERATOR_RUNNING = False
            remove_excess_linked(0, self.SP_OBJ_IDENTIFIER)
            return {'CANCELLED'}

        if n in {'RET'} and event.ctrl:
            self.SP_OPERATOR_RUNNING = False
            return {'FINISHED'}

        defined_keys = {'LEFT_BRACKET', 'RIGHT_BRACKET', 'DOWN_ARROW', 'UP_ARROW'}
        if (n in defined_keys) and (event.value == 'PRESS'):
            if self.handle_user_interaction(context, event):
                return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            scn = context.scene
            self.SP_OPERATOR_RUNNING = True
            self.SP_NUM_ITEMS = 3
            self.SP_OBJ_IDENTIFIER = obj_id(self)
            self.SP_RANDOM_SEED = 0
            self.add_between_duplicate_linked(
                num_items=self.SP_NUM_ITEMS,
                rand=self.SP_RANDOM_SEED)

            context.window_manager.modal_handler_add(self)
            print('start')
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}


def register():
    bpy.utils.register_class(ModalPrimitiveRepeat)


def unregister():
    bpy.utils.unregister_class(ModalPrimitiveRepeat)
