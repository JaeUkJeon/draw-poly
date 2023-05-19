from vtkmodules.vtkInteractionStyle import vtkInteractorStyleImage
from vtkmodules.vtkRenderingCore import vtkCellPicker
from vtkmodules.vtkCommonCore import vtkIdList


class MouseInteractorStyle(vtkInteractorStyleImage):
    def __init__(self, data, select_callback, change_callback, center_points, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.AddObserver('LeftButtonPressEvent', self.left_button_press_event)
        self.AddObserver('LeftButtonReleaseEvent', self.left_button_release_event)
        self.AddObserver('RightButtonPressEvent', self.right_button_press_event)
        self.AddObserver('MouseMoveEvent', self.mouse_move_event)
        self.AddObserver('MouseWheelForwardEvent', self.scroll_event)
        self.AddObserver('MouseWheelBackwardEvent', self.scroll_event)
        # self.AddObserver('KeyPressEvent', self.key_press_event)
        self.AddObserver('CharEvent', self.char_event)
        self.data = data
        self.callback_select = select_callback
        self.callback_change = change_callback
        self.center_points = center_points
        # self.callback_save = save_callback
        self.point_list = set()
        self.mouse_clicked = False
        self.remove_mode = False

    def pick_cell(self):
        # Get the location of the click (in window coordinates)
        pos = self.GetInteractor().GetEventPosition()

        picker = vtkCellPicker()
        picker.SetTolerance(0.0005)

        # Pick from this location.
        picker.Pick(pos[0], pos[1], 0, self.GetDefaultRenderer())

        return picker.GetCellId()

    def scroll_event(self, obj, event):
        scale = self.GetDefaultRenderer().GetActiveCamera().GetParallelScale()
        if event == 'MouseWheelForwardEvent':
            if scale < 2:
                return
            self.OnMouseWheelForward()
        elif event == 'MouseWheelBackwardEvent':
            if scale > 20:
                return
            self.OnMouseWheelBackward()

    def right_button_press_event(self, obj, event):
        if self.GetInteractor().GetShiftKey() or self.GetInteractor().GetControlKey():
            return
        cell_id = self.pick_cell()

        if cell_id != -1:
            poly = self.data
            pt = vtkIdList()
            poly.GetCellPoints(cell_id, pt)

            for i in range(pt.GetNumberOfIds()):
                if pt.GetId(i) in self.center_points:
                    self.callback_change(pt.GetId(i))

        # self.OnRightButtonDown()

    def left_button_press_event(self, obj, event):
        if self.GetInteractor().GetShiftKey():
            return

        self.remove_mode = False
        if self.GetInteractor().GetControlKey():
            self.remove_mode = True
        self.mouse_clicked = True

        cell_id = self.pick_cell()

        if cell_id != -1:
            poly = self.data
            pt = vtkIdList()
            poly.GetCellPoints(cell_id, pt)

            for i in range(pt.GetNumberOfIds()):
                if pt.GetId(i) in self.center_points:
                    self.callback_select(pt.GetId(i), self.remove_mode)

        # Forward events
        # self.OnLeftButtonDown()

    def mouse_move_event(self, obj, event):
        if self.mouse_clicked:
            cell_id = self.pick_cell()

            if cell_id != -1:
                poly = self.data
                pt = vtkIdList()
                poly.GetCellPoints(cell_id, pt)

                for i in range(pt.GetNumberOfIds()):
                    if pt.GetId(i) in self.center_points:
                        self.callback_select(pt.GetId(i), self.remove_mode)

        self.OnMouseMove()

    def left_button_release_event(self, obj, event):
        self.mouse_clicked = False

        self.OnLeftButtonUp()

    def char_event(self, obj, event):
        return
