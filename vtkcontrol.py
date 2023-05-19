import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import (
    vtkIdTypeArray,
    vtkPoints,
    vtkIdList
)
from vtkmodules.vtkCommonDataModel import (
    vtkSelection,
    vtkSelectionNode,
    vtkUnstructuredGrid,
    vtkPolyData,
    vtkPolyLine,
    vtkCellArray,
    vtkPolygon
)
from vtkmodules.vtkFiltersCore import vtkDelaunay2D
from vtkmodules.vtkFiltersGeometry import vtkDataSetSurfaceFilter
from vtkmodules.vtkFiltersExtraction import vtkExtractSelection
from vtkmodules.vtkFiltersModeling import vtkSelectEnclosedPoints

from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkDataSetMapper,
    vtkPolyDataMapper,
    vtkRenderer
)
from vtkmodules.vtkIOPLY import (
    vtkPLYWriter
)

from Constant import GRID_SIZE
from MouseInteractorStyle import MouseInteractorStyle
from MouseInteractorStyle2 import MouseInteractorStyle2

import math


def set_to_id_type_array(cell_set):
    arr = vtkIdTypeArray()
    for cell in cell_set:
        arr.InsertNextValue(cell)
    return arr


class VTKControl:
    def __init__(self, parent):
        if parent is None:
            return
        self.ren = vtkRenderer()
        self.ren_win = parent.GetRenderWindow()
        self.ren_win.AddRenderer(self.ren)
        self.iren = self.ren_win.GetInteractor()
        self.colors = vtkNamedColors()

        self.grid_data = vtkPolyData()

        self.selection_node = vtkSelectionNode()
        self.selection = vtkSelection()
        self.extract_selection = vtkExtractSelection()
        self.select_cell_point_ids = {}
        self.select_cell_ids = set()
        self.select_point_ids = []
        self.center_points = set()
        self.selected_node_polydata = vtkPolyData()
        self.selected_mapper = vtkDataSetMapper()
        self.selected_actor = vtkActor()
        self.selected_polygon_mapper = vtkDataSetMapper()
        self.selected_polygon_actor = vtkActor()

        self.context_pass_point_id = 0
        self.context_menu_count = 0

        self.iren.SetRenderWindow(self.ren_win)

        self.iren.Initialize()
        self.current_interactor_style = 0
        self.current_grid_type = 0

        self.init_view(self.current_grid_type, self.current_interactor_style)

        self.ren.SetBackground(self.colors.GetColor3d('PaleGreen'))
        self.ren.GetActiveCamera().ParallelProjectionOn()
        self.ren.ResetCamera()
        self.ren.GetActiveCamera().Zoom(10)

        self.ren_win.Render()

    def reset_member_variables(self):
        self.select_cell_point_ids.clear()
        self.select_cell_ids.clear()
        self.select_point_ids.clear()

        self.selection = vtkSelection()
        self.selection_node = vtkSelectionNode()
        self.selection_node.SetContentType(vtkSelectionNode.INDICES)
        self.selection_node.SetFieldType(vtkSelectionNode.CELL)

        self.selection.AddNode(self.selection_node)
        self.extract_selection.SetInputData(0, self.grid_data)
        self.extract_selection.SetInputData(1, self.selection)
        self.extract_selection.Update()
        self.selected_node_polydata = vtkPolyData()

        self.selected_mapper.SetInputConnection(self.extract_selection.GetOutputPort())

        self.selected_actor.SetMapper(self.selected_mapper)
        self.selected_actor.GetProperty().EdgeVisibilityOff()
        self.selected_actor.GetProperty().SetColor(self.colors.GetColor3d('Plum'))

    def init_view(self, grid_type, interactor_style):
        self.current_grid_type = grid_type
        self.current_interactor_style = interactor_style
        self.ren.RemoveAllViewProps()
        self.reset_member_variables()

        if grid_type == 0:
            self.init_quad_grid()
        elif grid_type == 1:
            self.init_hexagon_grid()

        if interactor_style == 0:  # Mesh
            self.selection_node.SetFieldType(vtkSelectionNode.CELL)
            self.selected_actor.GetProperty().RenderPointsAsSpheresOff()
            self.selected_actor.GetProperty().SetPointSize(1.0)
            style = MouseInteractorStyle(self.grid_data, self.select_mesh_callback, self.get_right_click_callback, self.center_points)
            style.SetDefaultRenderer(self.ren)
            self.iren.SetInteractorStyle(style)
        elif interactor_style == 1:  # Node
            self.selection_node.SetFieldType(vtkSelectionNode.POINT)
            self.selected_actor.GetProperty().RenderPointsAsSpheresOn()
            self.selected_actor.GetProperty().SetPointSize(10.0)
            style = MouseInteractorStyle2(self.select_point_callback, self.get_right_click_callback)
            style.SetDefaultRenderer(self.ren)
            self.iren.SetInteractorStyle(style)

        self.ren_win.Render()

    def select_mesh_callback(self, point_id, remove_mode):
        # select_ids.add(id)
        if remove_mode:
            if point_id in self.select_cell_point_ids:
                del self.select_cell_point_ids[point_id]
                cl = vtkIdList()
                self.grid_data.GetPointCells(point_id, cl)
                for idx in range(cl.GetNumberOfIds()):
                    if cl.GetId(idx) in self.select_cell_ids:
                        self.select_cell_ids.remove(cl.GetId(idx))
                self.selection_node.SetSelectionList(set_to_id_type_array(self.select_cell_ids))
        else:
            if point_id not in self.select_cell_point_ids:
                self.select_cell_point_ids[point_id] = 0
                # selected_ids = vtkIdTypeArray()
                cl = vtkIdList()
                self.grid_data.GetPointCells(point_id, cl)
                for idx in range(cl.GetNumberOfIds()):
                    self.select_cell_ids.add(cl.GetId(idx))
                self.selection_node.SetSelectionList(set_to_id_type_array(self.select_cell_ids))
        self.ren_win.Render()

    def select_point_callback(self, point_id, remove_mode):
        if point_id not in self.center_points:
            if remove_mode:
                if point_id in self.select_point_ids:
                    self.select_point_ids.remove(point_id)
            else:
                if point_id not in self.select_point_ids:
                    self.select_point_ids.append(point_id)

        select_ids = vtkIdTypeArray()
        polygon = vtkPolygon()
        for pid in self.select_point_ids:
            select_ids.InsertNextValue(pid)
            polygon.GetPointIds().InsertNextId(pid)
        polygon_ca = vtkCellArray()
        polygon_ca.InsertNextCell(polygon)
        self.selection_node.SetSelectionList(select_ids)
        self.selected_node_polydata.SetPolys(polygon_ca)

        self.ren_win.Render()

    def change_mesh(self, point_id, shape):
        if point_id in self.select_cell_point_ids:
            self.select_cell_point_ids[point_id] = shape % (9 if self.current_grid_type == 0 else 19 if self.current_grid_type == 1 else -1)
            cl = vtkIdList()
            self.grid_data.GetPointCells(point_id, cl)
            cell_bounds_center = {}
            for idx in range(cl.GetNumberOfIds()):
                self.select_cell_ids.add(cl.GetId(idx))
                bounds = self.grid_data.GetCell(cl.GetId(idx)).GetBounds()
                bounds_center = [bounds[0] + ((bounds[1] - bounds[0]) / 2),
                                 bounds[2] + ((bounds[3] - bounds[2]) / 2)]
                cell_bounds_center[idx] = bounds_center
            cell_bounds_center = sorted(cell_bounds_center.items(), key=lambda item: item[1])
            cell_remove = []
            if self.current_grid_type == 0:
                if self.select_cell_point_ids[point_id] == 1:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                elif self.select_cell_point_ids[point_id] == 2:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                elif self.select_cell_point_ids[point_id] == 3:
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
                elif self.select_cell_point_ids[point_id] == 4:
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
                elif self.select_cell_point_ids[point_id] == 5:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                elif self.select_cell_point_ids[point_id] == 6:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
                elif self.select_cell_point_ids[point_id] == 7:
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
                elif self.select_cell_point_ids[point_id] == 8:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
            elif self.current_grid_type == 1:
                if self.select_cell_point_ids[point_id] == 1:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[4][0]))
                elif self.select_cell_point_ids[point_id] == 2:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                elif self.select_cell_point_ids[point_id] == 3:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
                elif self.select_cell_point_ids[point_id] == 4:
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[5][0]))
                elif self.select_cell_point_ids[point_id] == 5:
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[4][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[5][0]))
                elif self.select_cell_point_ids[point_id] == 6:
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[4][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[5][0]))
                elif self.select_cell_point_ids[point_id] == 7:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[4][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[5][0]))
                elif self.select_cell_point_ids[point_id] == 8:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[4][0]))
                elif self.select_cell_point_ids[point_id] == 9:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
                elif self.select_cell_point_ids[point_id] == 10:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[5][0]))
                elif self.select_cell_point_ids[point_id] == 11:
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[4][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[5][0]))
                elif self.select_cell_point_ids[point_id] == 12:
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[4][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[5][0]))
                elif self.select_cell_point_ids[point_id] == 13:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[4][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[5][0]))
                elif self.select_cell_point_ids[point_id] == 14:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[4][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[5][0]))
                elif self.select_cell_point_ids[point_id] == 15:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[4][0]))
                elif self.select_cell_point_ids[point_id] == 16:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[5][0]))
                elif self.select_cell_point_ids[point_id] == 17:
                    cell_remove.append(cl.GetId(cell_bounds_center[0][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[4][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[5][0]))
                elif self.select_cell_point_ids[point_id] == 18:
                    cell_remove.append(cl.GetId(cell_bounds_center[1][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[2][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[3][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[4][0]))
                    cell_remove.append(cl.GetId(cell_bounds_center[5][0]))
            for cell in cell_remove:
                self.select_cell_ids.remove(cell)
            self.selection_node.SetSelectionList(set_to_id_type_array(self.select_cell_ids))
            self.ren_win.Render()

    def get_right_click_callback(self, point_id):
        self.context_pass_point_id = point_id
        if point_id in self.select_cell_point_ids:
            if self.current_grid_type == 0:
                self.context_menu_count = 9
            elif self.current_grid_type == 1:
                self.context_menu_count = 19
        else:
            self.context_menu_count = 0

    def get_number_context_menu(self):
        return self.context_pass_point_id, self.context_menu_count

    def regenerate_unstructured_grid(self):
        output_grid = vtkUnstructuredGrid()
        for key in self.select_cell_point_ids.keys():
            cell_array = vtkIdList()
            self.grid_data.GetPointCells(key, cell_array)
            dict_points = {}
            for idx in range(cell_array.GetNumberOfIds()):
                if cell_array.GetId(idx) in self.select_cell_ids:
                    point_array = vtkIdList()
                    self.grid_data.GetCellPoints(cell_array.GetId(idx), point_array)
                    for pt_arr_idx in range(point_array.GetNumberOfIds()):
                        if self.select_cell_point_ids[key] < 5:
                            if point_array.GetId(pt_arr_idx) < GRID_SIZE * GRID_SIZE:
                                dict_points[point_array.GetId(pt_arr_idx)] = self.grid_data \
                                    .GetPoint(point_array.GetId(pt_arr_idx))
                        else:
                            dict_points[point_array.GetId(pt_arr_idx)] = self.grid_data \
                                .GetPoint(point_array.GetId(pt_arr_idx))
            list_sorted = sorted(dict_points.items(), key=lambda item: item[1], reverse=True)
            list_points = []
            for point in list_sorted:
                list_points.append(point[0])
            if len(list_points) == 3:
                if self.select_cell_point_ids[key] == 3 or self.select_cell_point_ids[key] == 4 or \
                        self.select_cell_point_ids[key] == 6 or self.select_cell_point_ids[key] == 7:
                    temp = list_points[2]
                    list_points[2] = list_points[1]
                    list_points[1] = temp
                output_grid.InsertNextCell(5, 3, list_points)  # 5 : vtkCellTypes::VTK_TRIANGLE
            elif len(list_points) == 4:
                temp = list_points[3]
                list_points[3] = list_points[2]
                list_points[2] = temp
                output_grid.InsertNextCell(9, 4, list_points)  # 9 : vtkCellTypes:VTK_QUAD
            else:
                print('something wrong: ', list_points)
        output_grid.SetPoints(self.grid_data.GetPoints())

        return output_grid

    def check_save_possible(self):
        if self.extract_selection.GetOutput().GetNumberOfCells() == 0:
            return False
        elif self.extract_selection.GetOutput().GetNumberOfPoints() == 0:
            return False
        return True

    def save_ply(self, path='test.ply'):
        if self.extract_selection.GetOutput().GetNumberOfCells() == 0:
            return -1
        writer = vtkPLYWriter()
        writer.SetFileName(path)

        if self.current_interactor_style == 0 and self.current_grid_type == 0:
            surface_filter = vtkDataSetSurfaceFilter()
            surface_filter.SetInputData(self.regenerate_unstructured_grid())
            writer.SetInputConnection(surface_filter.GetOutputPort())
        elif self.current_interactor_style == 0 and self.current_grid_type == 1:
            surface_filter = vtkDataSetSurfaceFilter()
            surface_filter.SetInputConnection(self.extract_selection.GetOutputPort())
            writer.SetInputConnection(surface_filter.GetOutputPort())
        elif self.current_interactor_style == 1:
            enclosed = vtkSelectEnclosedPoints()
            enclosed.SetInputData(self.grid_data)
            enclosed.SetSurfaceData(self.selected_node_polydata)
            enclosed.Update()

            enclosed_points = vtkPoints()
            for i in range(self.grid_data.GetNumberOfPoints()):
                if enclosed.IsInside(i) == 1:
                    enclosed_points.InsertNextPoint(self.grid_data.GetPoint(i))

            new_ca = vtkCellArray()
            new_ca.InsertNextCell(self.selected_node_polydata.GetCell(0))

            enclosed_poly = vtkPolyData()
            enclosed_poly.SetPoints(enclosed_points)
            enclosed_poly.SetPolys(new_ca)

            # Triangulate the grid points
            delaunay = vtkDelaunay2D()
            delaunay.SetInputData(enclosed_poly)
            delaunay.Update()

            writer.SetInputConnection(delaunay.GetOutputPort(0))

        writer.SetFileTypeToASCII()
        return writer.Write()

    def init_quad_grid(self):
        # Create points on an XY grid with random Z coordinate
        points = vtkPoints()
        grid_size = GRID_SIZE

        self.selection_node.SetFieldType(vtkSelectionNode.CELL)
        self.selection_node.SetContentType(vtkSelectionNode.INDICES)
        self.selection.AddNode(self.selection_node)

        ca = vtkCellArray()
        for y in range(0, grid_size):
            poly_line = vtkPolyLine()
            for x in range(0, grid_size):
                points.InsertNextPoint(x, y, 0)
                poly_line.GetPointIds().InsertNextId(y * grid_size + x)
            ca.InsertNextCell(poly_line)

        for x in range(0, grid_size):
            poly_line = vtkPolyLine()
            for y in range(0, grid_size):
                poly_line.GetPointIds().InsertNextId(y * grid_size + x)
            ca.InsertNextCell(poly_line)

        self.center_points.clear()
        c_point = points.GetNumberOfPoints()
        for j in range(0, grid_size - 1):
            for i in range(0, grid_size - 1):
                points.InsertNextPoint(i + 0.5, j + 0.5, 0)
                self.center_points.add(c_point)
                c_point = c_point + 1

        # Add the grid points to a polyData object
        poly_data = vtkPolyData()
        poly_data.SetPoints(points)

        # poly_grid_line = vtkPolyData()
        # poly_grid_line.SetPoints(points)
        # poly_grid_line.SetLines(ca)
        #
        # grid_line_mapper = vtkPolyDataMapper()
        # grid_line_mapper.SetInputData(poly_grid_line)
        #
        # grid_line_actor = vtkActor()
        # grid_line_actor.SetMapper(grid_line_mapper)
        # grid_line_actor.GetProperty().SetColor(self.colors.GetColor3d("Black"))
        # grid_line_actor.GetProperty().SetLineWidth(3)
        # grid_line_actor.PickableOff()

        # Triangulate the grid points
        delaunay = vtkDelaunay2D()
        delaunay.SetInputData(poly_data)
        delaunay.Update()

        self.grid_data.ShallowCopy(delaunay.GetOutput())
        self.grid_data.SetLines(ca)
        self.selected_node_polydata.SetPoints(points)

        self.selected_polygon_mapper.SetInputData(self.selected_node_polydata)

        self.selected_polygon_actor.SetMapper(self.selected_polygon_mapper)
        self.selected_polygon_actor.GetProperty().EdgeVisibilityOff()
        self.selected_polygon_actor.GetProperty().SetColor(self.colors.GetColor3d('Plum'))

        # Create a mapper and actor
        triangulated_mapper = vtkPolyDataMapper()
        triangulated_mapper.SetInputData(self.grid_data)

        triangulated_actor = vtkActor()
        triangulated_actor.SetMapper(triangulated_mapper)
        triangulated_actor.GetProperty().SetColor(self.colors.GetColor3d('Black'))
        triangulated_actor.GetProperty().SetOpacity(0.3)
        triangulated_actor.GetProperty().SetLineWidth(3)

        # renderer.AddActor(pointsActor)
        # self.ren.AddActor(grid_line_actor)
        self.ren.AddActor(triangulated_actor)
        self.ren.AddActor(self.selected_actor)
        self.ren.AddActor(self.selected_polygon_actor)
        # renderer.ResetCamera()

    def init_hexagon_grid(self):
        # Create points on an XY grid with random Z coordinate
        points = vtkPoints()
        grid_size = (GRID_SIZE if GRID_SIZE % 2 == 0 else GRID_SIZE - 1) * 3

        self.selection_node.SetFieldType(vtkSelectionNode.CELL)
        self.selection_node.SetContentType(vtkSelectionNode.INDICES)
        self.selection.AddNode(self.selection_node)

        for y in range(0, grid_size):
            for x in range(0, grid_size):
                if y % 2 == 0 and x % 2 == 1:
                    points.InsertNextPoint(x * 0.5, y * math.sin(math.pi / 3), 0)
                elif y % 2 == 1 and x % 2 == 0:
                    points.InsertNextPoint(x * 0.5, y * math.sin(math.pi / 3), 0)

        ca_line = vtkCellArray()
        half = math.floor(grid_size / 2)
        remain = half % 3
        for j in range(half - 1):
            i = 0
            while i < grid_size - 1:
                polyline = vtkPolyLine()
                polyline.GetPointIds().SetNumberOfIds(7)
                if i <= half <= i + 3:
                    i = i + 3
                    continue
                elif i < half:
                    polyline.GetPointIds().SetId(0, j * grid_size + i)
                    polyline.GetPointIds().SetId(1, j * grid_size + i + 1)
                    polyline.GetPointIds().SetId(2, j * grid_size + i + half + 2)
                    polyline.GetPointIds().SetId(3, (j + 1) * grid_size + i + 1)
                    polyline.GetPointIds().SetId(4, (j + 1) * grid_size + i)
                    polyline.GetPointIds().SetId(5, j * grid_size + i + half)
                    polyline.GetPointIds().SetId(6, j * grid_size + i)
                elif i > half:
                    polyline.GetPointIds().SetId(0, j * grid_size + i - 1 + remain)
                    polyline.GetPointIds().SetId(1, j * grid_size + i + remain)
                    polyline.GetPointIds().SetId(2, j * grid_size + i + half + remain)
                    polyline.GetPointIds().SetId(3, (j + 1) * grid_size + i + remain)
                    polyline.GetPointIds().SetId(4, (j + 1) * grid_size + i - 1 + remain)
                    polyline.GetPointIds().SetId(5, j * grid_size + i + half + remain - 2)
                    polyline.GetPointIds().SetId(6, j * grid_size + i - 1 + remain)
                ca_line.InsertNextCell(polyline)
                i = i + 3

        center_points0 = []
        i = 0
        while i < grid_size - 1:
            if i <= half <= i + 3:
                i = i + 3
                continue
            elif i < half:
                center_points0.append(half + 1 + i)
            elif i > half:
                center_points0.append(half + remain - 1 + i)
            i = i + 3

        self.center_points.clear()
        for pid in center_points0:
            self.center_points.add(int(pid))
            iteration = grid_size
            while iteration < points.GetNumberOfPoints():
                if pid + iteration < points.GetNumberOfPoints():
                    self.center_points.add(int(pid + iteration))
                iteration = iteration + grid_size

        # Add the grid points to a polyData object
        poly_data = vtkPolyData()
        poly_data.SetPoints(points)

        delaunay = vtkDelaunay2D()
        delaunay.SetInputData(poly_data)
        delaunay.Update()

        poly = vtkPolyData()
        poly.DeepCopy(delaunay.GetOutput())
        poly.SetLines(ca_line)

        self.grid_data.ShallowCopy(poly)

        mapper = vtkPolyDataMapper()
        mapper.SetInputData(self.grid_data)

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(self.colors.GetColor3d('Black'))
        actor.GetProperty().SetOpacity(0.3)
        actor.GetProperty().SetLineWidth(3)

        self.selected_node_polydata.SetPoints(points)

        self.selected_polygon_mapper.SetInputData(self.selected_node_polydata)

        self.selected_polygon_actor.SetMapper(self.selected_polygon_mapper)
        self.selected_polygon_actor.GetProperty().EdgeVisibilityOff()
        self.selected_polygon_actor.GetProperty().SetColor(self.colors.GetColor3d('Plum'))

        self.ren.AddActor(actor)
        self.ren.AddActor(self.selected_actor)
        self.ren.AddActor(self.selected_polygon_actor)
