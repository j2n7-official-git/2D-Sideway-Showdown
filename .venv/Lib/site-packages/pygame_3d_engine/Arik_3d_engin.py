from math import sin, cos, radians
from random import randint
from copy import deepcopy
import numpy
from time import time



class CustomModel(object):
    def __init__(self, vertecies, edges, faces, face_colors = [], edge_colors = [], center = [0, 0, 0]):
        self.is_shadow = False
        self.vertecies = [[v[0] + center[0], v[1] + center[1], v[2] + center[2]] for v in vertecies]
        self.og_vertecies = deepcopy(self.vertecies)
        self.center = [numpy.array(self.vertecies)[:, 0].mean(), numpy.array(self.vertecies)[:, 1].mean(), numpy.array(self.vertecies)[:, 2].mean()]
        self._h_angle = 0
        self.shadows_on = False
        self.hit = False
        self.faces = faces
        self.edges = edges

        if not face_colors:
            self.face_colors = [(randint(0, 255), randint(0, 255), randint(0, 255)) for _ in self.faces]
        elif type(face_colors) == tuple:
            self.face_colors = [face_colors for _ in self.faces]
        else:
            self.face_colors = face_colors
        
        if not edge_colors:
            self.edge_colors = [(randint(0, 255), randint(0, 255), randint(0, 255)) for _ in self.faces]
        elif type(edge_colors) == tuple:
            self.edge_colors = [edge_colors for _ in self.edges]
        else:
            self.edge_colors = edge_colors

    def shadow(self):
        self.shadows_on = True
        shadow_vertecies = [[vertex[0], -50, vertex[2]] for vertex in self.vertecies]
        shadow_og_vertecies = [[vertex[0], -50, vertex[2]] for vertex in self.og_vertecies]
        self.shadow_obj = CustomModel(shadow_vertecies, [], self.faces, face_colors=(50, 50, 50))
        self.shadow_obj.vertecies = shadow_vertecies
        self.shadow_obj.og_vertecies = shadow_og_vertecies
        self.shadow_obj.is_shadow = True
        return self.shadow_obj
    

    @property
    def h_look_cos(self):
        return cos(radians(self.h_angle))
    
    @property
    def h_look_sin(self):
        return sin(radians(self.h_angle))
    
    @property
    def h_angle(self):
        return self._h_angle
    
    @h_angle.setter
    def h_angle(self, value):
        self._h_angle = value
        self._h_angle %= 360
        self.rotate_y_axis()

        if self.shadows_on:
            self.shadow_obj.h_angle = self._h_angle

    
    def rotate_y_axis(self):
        for i, vertex in enumerate(self.og_vertecies):
            vertex = vertex[0] - self.center[0], vertex[1] - self.center[1], vertex[2] - self.center[2]
            rx = vertex[0] * self.h_look_cos + vertex[2] * -self.h_look_sin + self.center[0]
            ry = vertex[1] + self.center[1]
            rz = vertex[0] * self.h_look_sin + vertex[2] * self.h_look_cos + self.center[2]
            self.vertecies[i] = [rx, ry, rz]

    
    def __repr__(self):
        return f"CustomObject: ({round(self.center[0], 3)}, {round(self.center[1], 3)}, {round(self.center[2], 3)}), v:{len(self.vertecies)}, e: {len(self.edges)}, f:{len(self.faces)}"



class Grid(object):
    def __init__(self, center = [0, 0, 0], width = 10, height = 10, seprate = 50, ground_level = -50):
        self.is_shadow = False
        self.vertecies = []
        self.center = center
        self.shadows_on = True
        self.faces = []
        self.face_colors = []
        self.edges = []
        self.edge_colors = []
        self.hit = False
        self.h_angle = 0

        for x in range(-width // 2 * seprate, width // 2 * seprate + 1, seprate):
                self.vertecies.append([x, ground_level, height // 2 * seprate])
                self.vertecies.append([x, ground_level, -height // 2 * seprate])

        for y in range(-height // 2 * seprate, height // 2 * seprate + 1, seprate):
                self.vertecies.append([width // 2 * seprate, ground_level, y])
                self.vertecies.append([-width // 2 * seprate, ground_level, y])

        self.edges += [[i, i + 1] for i in range(0, len(self.vertecies) // 2, 2)]
        self.edges += [[i, i + 1] for i in range(len(self.vertecies) // 2, len(self.vertecies), 2)]
        self.edge_colors = [(0, 0, 0) for _ in self.edges]


    def __repr__(self):
        return f"Grid: ({self.center[0]}, {self.center[1]}, {self.center[2]}), v:{len(self.vertecies)}, e: {len(self.edges)}, f:{len(self.faces)}"



class Cube(object):
    def __init__(self, center = [0, 0, 0], edge_size = 10, face_colors = [], edge_colors = []):
        self.is_shadow = False
        self.vertecies = []
        self.og_vertecies = []
        self.center = center
        self.edge_size = edge_size
        self._h_angle = 0
        self.shadows_on = False
        self.hit = False

        for x in range(-edge_size, edge_size + 1, edge_size * 2):
            for y in range(-edge_size, edge_size + 1, edge_size * 2):
                for z in range(-edge_size, edge_size + 1, edge_size * 2):
                    self.vertecies.append([center[0] + x, center[1] + y, center[2] + z])
                    self.og_vertecies.append([center[0] + x, center[1] + y, center[2] + z])

        self.faces = [[2, 0, 1, 3], [6, 4, 5, 7], [3, 1, 5, 7], [0, 2, 6, 4], [3, 2, 6, 7], [1, 0, 4, 5]]
        self.edges = [[2, 0, 1, 3], [6, 4, 5, 7], [3, 1, 5, 7], [0, 2, 6, 4], [3, 2, 6, 7], [1, 0, 4, 5]]
        
        if not face_colors:
            self.face_colors = [(randint(0, 255), randint(0, 255), randint(0, 255)) for _ in self.faces]
        elif type(face_colors) == tuple:
            self.face_colors = [face_colors for _ in self.faces]
        else:
            self.face_colors = face_colors
        
        if not edge_colors:
            self.edge_colors = [(randint(0, 255), randint(0, 255), randint(0, 255)) for _ in self.faces]
        elif type(edge_colors) == tuple:
            self.edge_colors = [edge_colors for _ in self.edges]
        else:
            self.edge_colors = edge_colors


    def shadow(self):
        self.shadows_on = True
        shadow_vertecies = [[vertex[0], -50, vertex[2]] for vertex in self.vertecies]
        shadow_og_vertecies = [[vertex[0], -50, vertex[2]] for vertex in self.og_vertecies]
        shadow_faces = [face for face in self.faces]
        self.shadow_obj = Cube(self.center, self.edge_size, edge_colors=(50, 50, 50), face_colors=(50, 50, 50))
        self.shadow_obj.vertecies = shadow_vertecies
        self.shadow_obj.og_vertecies = shadow_og_vertecies
        self.shadow_obj.faces = shadow_faces
        self.shadow_obj.is_shadow = True
        return self.shadow_obj


    @property
    def h_look_cos(self):
        return cos(radians(self.h_angle))
    

    @property
    def h_look_sin(self):
        return sin(radians(self.h_angle))
    
    @property
    def h_angle(self):
        return self._h_angle
    
    @h_angle.setter
    def h_angle(self, value):
        self._h_angle = value
        self._h_angle %= 360
        self.rotate_y_axis()

        if self.shadows_on:
            self.shadow_obj.h_angle = self._h_angle

    
    def rotate_y_axis(self):
        for i, vertex in enumerate(self.og_vertecies):
            vertex = vertex[0] - self.center[0], vertex[1] - self.center[1], vertex[2] - self.center[2]
            rx = vertex[0] * self.h_look_cos + vertex[2] * -self.h_look_sin + self.center[0]
            ry = vertex[1] + self.center[1]
            rz = vertex[0] * self.h_look_sin + vertex[2] * self.h_look_cos + self.center[2]
            self.vertecies[i] = [rx, ry, rz]


    def __repr__(self):
        return f"Cube: ({self.center[0]}, {self.center[1]}, {self.center[2]}), v:{len(self.vertecies)}, e: {len(self.edges)}, f:{len(self.faces)}"



class World(object):
    def __init__(self, objects = [], fov = 10, fps = 75, gravity = 0.1, jump_strength = 2.5, friction = 0.03, shadow_color = (30, 30, 30)):
        self.fov = fov
        self.fps = fps
        self.gravity = gravity
        self.sensitivity = 0.2
        self.shadow_color = shadow_color
        self.shading = False

        self.objects = objects
        self.rendered_vertecies = []
        self.rendered_edges = []
        self.rendered_edge_colors = []
        self.rendered_faces = []
        self.rendered_face_colors = []
        self.deapth_controll_f = []
        self.deapth_controll_e = []
        self.obj_look_up_f = []
        self.obj_look_up_e = []
        self.obj_look_up_f_e = []
        self.rendered_f_e = []
        self.rendered_f_e_colors = []
        self.f_e_look_up = []
        self.render_time_track = []

        self.shift = [0, 0, 0]
        self.horizantle_angle = 0
        self.vertical_angle = 0

        self.move_speed = fps
        self.speed_multiplier = 1

        self.acceleration = [0, 0, 0]
        self.acceleration_relation = [0, 0, 0]
        self.friction = friction
        self.jump_strength = jump_strength

    
    @property
    def h_look_cos(self):
        self.horizantle_angle %= 360
        return cos(radians(self.horizantle_angle))
    

    @property
    def h_look_sin(self):
        self.horizantle_angle %= 360
        return sin(radians(self.horizantle_angle))
    

    @property
    def v_look_cos(self):
        self.vertical_angle = 90 if self.vertical_angle > 90 else (-90 if self.vertical_angle < -90 else self.vertical_angle)
        return cos(radians(self.vertical_angle))
    

    @property
    def v_look_sin(self):
        self.vertical_angle = 90 if self.vertical_angle > 90 else (-90 if self.vertical_angle < -90 else self.vertical_angle)
        return sin(radians(self.vertical_angle))
    
    
    def shift_forward(self):
        self.shift[2] -= self.move_speed / self.fps * self.h_look_cos * self.speed_multiplier
        self.shift[0] -= self.move_speed / self.fps * self.h_look_sin * self.speed_multiplier


    def shift_backward(self):
        self.shift[2] += self.move_speed / self.fps * self.h_look_cos * self.speed_multiplier
        self.shift[0] += self.move_speed / self.fps * self.h_look_sin * self.speed_multiplier


    def shift_left(self):
        self.horizantle_angle -= 90
        self.shift_forward()
        self.horizantle_angle += 90


    def shift_right(self):
        self.horizantle_angle += 90
        self.shift_forward()
        self.horizantle_angle -= 90


    def rotate_y_axis(self, vertex):
        rx = vertex[0] * self.h_look_cos + vertex[2] * -self.h_look_sin
        ry = vertex[1]
        rz = vertex[0] * self.h_look_sin + vertex[2] * self.h_look_cos
        return [rx, ry, rz]
    

    def rotate_x_axis(self, vertex):
        rx = vertex[0]
        ry = vertex[1] * self.v_look_cos + vertex[2] * self.v_look_sin
        rz = vertex[1] * -self.v_look_sin + vertex[2] * self.v_look_cos
        return [rx, ry, rz]


    def rotate_z_axis(self, vertex):
        rx = vertex[0] * -self.v_look_cos + vertex[1] * self.v_look_sin
        ry = vertex[0] * -self.v_look_sin + vertex[1] * self.v_look_cos
        rz = vertex[2]
        return [rx, ry, rz]
    

    def apply_shift(self, vertex):
        return [vertex[0] + self.shift[0], vertex[1] + self.shift[1], vertex[2] + self.shift[2]]
    

    def jump(self):
        if self.acceleration[1] == 0:
            self.acceleration[1] = -self.jump_strength


    def handle_acceleration(self):
        self.shift[1] += self.acceleration[1] / self.fps * 75
        self.acceleration[1] += self.gravity / self.fps * 75

        if self.shift[1]  + self.acceleration[1] > 0:
            self.shift[1] = 0
            self.acceleration[1] = 0

        for i in [0, 2]:
            is_pos = True if self.acceleration[i] > 0 else False
            self.shift[i] -= self.acceleration[i] / self.fps * 75
            self.acceleration[i] = self.acceleration[i] - self.friction * self.acceleration_relation[i] / self.fps * 75 if is_pos else self.acceleration[i] + self.friction * self.acceleration_relation[i] / self.fps * 75
            new_is_pos = True if self.acceleration[i] > 0 else False
            if is_pos is not new_is_pos:
                self.acceleration[i] = 0


    def smooth_stop_w(self):
        self.acceleration[2] = self.move_speed * self.h_look_cos * self.speed_multiplier / 75
        self.acceleration[0] = self.move_speed * self.h_look_sin * self.speed_multiplier / 75
        self.acceleration_relation[2] = abs(self.h_look_cos)
        self.acceleration_relation[0] = abs(self.h_look_sin)


    def smooth_stop_s(self):
        self.acceleration[2] = -self.move_speed * self.h_look_cos * self.speed_multiplier / 75
        self.acceleration[0] = -self.move_speed * self.h_look_sin * self.speed_multiplier / 75
        self.acceleration_relation[2] = abs(self.h_look_cos)
        self.acceleration_relation[0] = abs(self.h_look_sin)


    def smooth_stop_a(self):
        self.horizantle_angle -= 90
        self.smooth_stop_w()
        self.horizantle_angle += 90


    def smooth_stop_d(self):
        self.horizantle_angle += 90
        self.smooth_stop_w()
        self.horizantle_angle -= 90

    
    def color_mixer(self, s_rgb, e_rgb, percent):
        return (s_rgb[0] + percent * (e_rgb[0] - s_rgb[0]), s_rgb[1] + percent * (e_rgb[1] - s_rgb[1]), s_rgb[2] + percent * (e_rgb[2] - s_rgb[2]))


    def apply_render_priority(self):
        #  -- Faces --
        look_up = {}

        f_e_render = self.rendered_faces + self.rendered_edges
        f_e_color_render = self.rendered_face_colors + self.rendered_edge_colors
        f_e_deapth = self.deapth_controll_f + self.deapth_controll_e
        f_e_look_up = ['f' for _ in self.rendered_faces] + ['e' for _ in self.rendered_edges]
        f_e_obj_look_up = self.obj_look_up_f + self.obj_look_up_e
        
        for i, z in enumerate(f_e_deapth):
            if not look_up.get(z):
                look_up[z] = [i]
            else:
                look_up[z].append(i)

        f_e_deapth.sort()
        new_f_e_list = []
        new_f_e_color_list = []
        new_f_e_look_up = []
        new_obj_look_up = []

        for z in f_e_deapth[::-1]:
            new_f_e_list.append(f_e_render[look_up[z][0]])
            new_f_e_color_list.append(f_e_color_render[look_up[z][0]])
            new_f_e_look_up.append(f_e_look_up[look_up[z][0]])
            new_obj_look_up.append(f_e_obj_look_up[look_up[z][0]])
            del look_up[z][0]

        self.rendered_f_e = new_f_e_list
        self.rendered_f_e_colors = new_f_e_color_list
        self.f_e_look_up = new_f_e_look_up
        self.obj_look_up_f_e = new_obj_look_up


    def render(self):
        self.rendered_vertecies = []
        self.rendered_edges = []
        self.rendered_edge_colors = []
        self.rendered_faces = []
        self.rendered_face_colors = []
        self.deapth_controll_f = []
        self.deapth_controll_e = []
        self.obj_look_up_f = []
        self.obj_look_up_e = []
        self.obj_look_up_f_e = []
        self.rendered_f_e_colors = []
        self.rendered_f_e = []
        self.f_e_look_up = []

        for obj in self.objects:
            on_screen_vertecies = set()
            off_screen_vertecies = []
            off_screen_deapth_controll = []

            for i, vertex in enumerate(obj.vertecies):
                new_vertex = self.apply_shift(vertex)
                new_vertex = self.rotate_y_axis(new_vertex)
                new_vertex = self.rotate_x_axis(new_vertex)

                new_vertex[2] = -.1 if -0.1 < new_vertex[2] < 0.1 else new_vertex[2]
                x_render = new_vertex[0] * self.fov / new_vertex[2]
                y_render = new_vertex[1] * self.fov / new_vertex[2]
                off_screen_deapth_controll.append(new_vertex[2])

                x_render, y_render = numpy.clip(-self.fov, self.fov, (x_render, y_render))

                if new_vertex[2] > 1:
                    self.rendered_vertecies.append((x_render, y_render))
                    on_screen_vertecies.add(i)
                    off_screen_vertecies.append((x_render, y_render))
                else:
                    off_screen_vertecies.append((-x_render, -y_render))

            for n, face in enumerate(obj.faces):
                if on_screen_vertecies.intersection(face):
                    self.rendered_faces.append([off_screen_vertecies[i] for i in face])
                    self.deapth_controll_f.append(sum([off_screen_deapth_controll[i] for i in face]) / len(face))
                    self.obj_look_up_f.append(obj)

                    if self.shading:
                        z_ = numpy.array([off_screen_deapth_controll[i] for i in face])
                        # depth_factor = (z_.mean() - z_.min()) / (z_.max() - z_.min() + 1e-5)
                        # depth_factor = numpy.clip(0, 1, z_.std() / 3)
                        depth_factor = 1 / (z_.std() / 2 + 1)
                        # color = self.color_mixer(obj.face_colors[n], self.shadow_color, depth_factor)
                        color = self.color_mixer(self.shadow_color, obj.face_colors[n], depth_factor)
                        self.rendered_face_colors.append(color)
                    else:
                        self.rendered_face_colors.append(obj.face_colors[n])

            for n, edge in enumerate(obj.edges):
                if on_screen_vertecies.intersection(edge):
                    self.rendered_edges.append([off_screen_vertecies[i] for i in edge])
                    self.rendered_edge_colors.append(obj.edge_colors[n])
                    self.deapth_controll_e.append(sum([off_screen_deapth_controll[i] for i in edge]) / len(edge))
                    self.obj_look_up_e.append(obj)
            
        self.apply_render_priority()
        self.render_time_track.append(time())
        if len(self.render_time_track) > 10:
            del self.render_time_track[0]

    
    def ray_trace_collion_detector(self, point, polygon):
        inside = False
        px, py = point

        for i in range(len(polygon)):
            x1, y1 = polygon[i]
            x2, y2 = polygon[i-1]
            
            if (py > y1) != (py > y2):
                if px < max([x1, x2]):
                    f = (x2 - x1) * (abs(py - min([y1, y2]))) / (y2 - y1)
                    relational_x = min([x1, x2]) + (f if f > 0 else f + abs(x1 - x2))
                    if px <= relational_x:
                        inside = not inside
        
        return inside
    

    def load_obj(self, file_name, scale = 1, center = [0, 0, 0], show_edge = True, edge_colors = (220, 220, 220), face_colors = (25, 25, 25)):
        with open(file_name, 'r') as f:
            obj = f.read().split('\n')

        converted_vertices = []
        converted_faces = []

        for s in obj:
            if s[:2] == 'v ':
                vertex = s[1:].split()
                for i, n in enumerate(vertex):
                    vertex[i] = float(n) * scale
                converted_vertices.append(vertex)
            
            if s[:2] == 'f ':
                f = s[1:].split()
                for i, n in enumerate(f):
                    f[i] = int(n.split('/')[0]) - 1
                converted_faces.append(f)


        return CustomModel(converted_vertices, converted_faces if show_edge else [], converted_faces, center=center, edge_colors=edge_colors, face_colors=face_colors)


    def render_fps(self):
        if len(self.render_time_track) == 10:
            self.fps = round(10 / (self.render_time_track[9] - self.render_time_track[0]))
        return self.fps


    def __repr__(self):
        return f"""-- World,
        Shading: {self.shading}, Shodow Color {self.shadow_color}, Sensitivity: {self.sensitivity}, Gravity: {self.gravity}
        Fov: {self.fov}, Fps: {self.fps}, Horizantle look: {self.horizantle_angle}, Vertical look: {self.vertical_angle}
        World position: {self.shift}, Jump strength: {self.jump_strength}, Friction: {self.friction}
        \nObjects: {'\n'.join(str(obj) for obj in self.objects)}
        """
