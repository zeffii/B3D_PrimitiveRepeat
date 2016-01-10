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
    "name": "quick dupe linked",
    "author": "Dealga McArdle",
    "version": (0, 1),
    "blender": (2, 7, 6),
    "category": "3D View"
}

import bpy
import time
import mathutils


def get_operator_id(caller):
    return str(hash(caller))


def remove_obj(obj):
    scene = bpy.context.scene
    objs = bpy.data.objects
    me = obj.data
    scene.objects.unlink(obj)
    objs.remove(obj)


def remove_excess_linked(idx, operator_id):
    for o in bpy.data.objects:
        if not (o.get('flux_operator_id') == operator_id):
            continue
        if o['flux_dupe_index'] > idx:
            remove_obj(o)


def make_or_update_dupe(idx, amt, props, MT):
    scene = bpy.context.scene
    objs = bpy.data.objects
    meshes = bpy.data.meshes

    obj = None
    for o in objs:
        if o.get('flux_operator_id') == props.operator_id:
            if o['flux_dupe_index'] == idx:
                obj = o
                break
    if not obj:
        obj = objs.new(props.linked_mesh_name, meshes.get(props.linked_mesh_name))
        obj['flux_dupe_index'] = idx
        obj['flux_operator_id'] = props.operator_id
        scene.objects.link(obj)

    if props.interpolate_matrices:
        A_MAT, B_MAT = props.a_mat, props.b_mat
        obj.matrix_world = A_MAT.lerp(B_MAT, amt)
    else:
        A, B = props.loc1, props.loc2
        obj.location = A.lerp(B, amt)

    obj.parent = MT


def main(props, context):
    scene = context.scene

    def make_or_reference_associated_empty():
        objects = bpy.data.objects
        MT_NAME = "FLUX_" + props.operator_id
        MT = objects.get(MT_NAME)
        if not MT:
            MT = objects.new(MT_NAME, None)
            scene.objects.link(MT)
        return MT

    MT = make_or_reference_associated_empty()

    print(props.linked_mesh_name)

    if props.num_repeats <= 0:
        remove_excess_linked(0, props.operator_id)
        # context.scene.objects.unlink(MT)
        return

    divcount = props.num_repeats + 1
    mode = props.selected_spread_mode

    if mode == 'linear':
        segment = (1.0 / divcount)
        f = [i * segment for i in range(1, divcount)]
    elif mode == 'deviate':
        ...
    elif mode == 'random':
        ...
    else:
        return

    for idx, amt in enumerate(f):
        make_or_update_dupe(idx, amt, props, MT)

    # any objects found with greater index can be removed
    remove_excess_linked(idx, props.operator_id)


class FluxOperator(bpy.types.Operator):
    bl_idname = "flux.my_operator"
    bl_label = "Simple flux"
    bl_options = {'REGISTER', 'UNDO'}

    linked_mesh_name = bpy.props.StringProperty()
    num_repeats = bpy.props.IntProperty(min=0, default=1)
    operator_id = bpy.props.StringProperty()

    spread_modes = enumerate(['linear', 'deviate', 'random'])
    selected_spread_mode = bpy.props.EnumProperty(
        items=[(mode, mode, "", idx) for idx, mode in spread_modes],
        description="offers....",
        default="linear"
    )

    interpolate_matrices = bpy.props.BoolProperty()

    @classmethod
    def poll(cls, context):
        active = context.active_object
        selected = context.selected_objects
        if active and selected and (len(selected) == 2):
            return selected[0].data == selected[1].data

    def execute(self, context):
        self.linked_mesh_name = context.active_object.data.name
        self.loc1, self.loc2 = [o.location for o in context.selected_objects]
        self.operator_id = get_operator_id(self)
        self.a_mat = context.selected_objects[0].matrix_world
        self.b_mat = context.selected_objects[1].matrix_world

        main(self, context)
        return {'FINISHED'}


def register():
    bpy.utils.register_class(FluxOperator)


def unregister():
    bpy.utils.unregister_class(FluxOperator)


if __name__ == "__main__":
    register()
