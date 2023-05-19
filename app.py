from PyQt6 import (
    QtWidgets,
    QtCore,
    QtGui
)
from mainwindow import Ui_MainWindow
from vtkcontrol import VTKControl


class MainView(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.vtk = VTKControl(self.ui.vtkWidget)
        self.ui.actionSave.triggered.connect(self.open_save_dialog)
        # self.ren = vtkRenderer()
        # self.ui.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        # self.iren = self.ui.vtkWidget.GetRenderWindow().GetInteractor()

        self.contextMenu = QtWidgets.QMenu(self.ui.vtkWidget)

        self.ui.actionQuad.triggered.connect(self.check_changed_quad)
        self.ui.actionHexagon.triggered.connect(self.check_changed_hexagon)
        self.ui.actionMesh.triggered.connect(self.check_changed_mesh)
        self.ui.actionNode.triggered.connect(self.check_changed_node)

        self.ui.actionMesh.setChecked(True)
        self.ui.actionQuad.setChecked(True)

        self.ui.vtkWidget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.vtkWidget.customContextMenuRequested.connect(self.open_context_menu)

    def check_changed_quad(self):
        if self.ui.actionQuad.isChecked():
            self.ui.actionHexagon.setChecked(False)
            self.vtk.init_view(0, 0 if self.ui.actionMesh.isChecked() else 1 if self.ui.actionNode.isChecked() else -1)
        else:
            self.ui.actionQuad.setChecked(True)

    def check_changed_hexagon(self):
        if self.ui.actionHexagon.isChecked():
            self.ui.actionQuad.setChecked(False)
            self.vtk.init_view(1, 0 if self.ui.actionMesh.isChecked() else 1 if self.ui.actionNode.isChecked() else -1)
        else:
            self.ui.actionHexagon.setChecked(True)

    def check_changed_mesh(self):
        if self.ui.actionMesh.isChecked():
            self.ui.actionNode.setChecked(False)
            self.vtk.init_view(0 if self.ui.actionQuad.isChecked() else 1 if self.ui.actionHexagon.isChecked() else -1, 0)
        else:
            self.ui.actionMesh.setChecked(True)

    def check_changed_node(self):
        if self.ui.actionNode.isChecked():
            self.ui.actionMesh.setChecked(False)
            self.vtk.init_view(0 if self.ui.actionQuad.isChecked() else 1 if self.ui.actionHexagon.isChecked() else -1, 1)
        else:
            self.ui.actionNode.setChecked(True)

    def open_save_dialog(self):
        ret = self.vtk.check_save_possible()
        if not ret:
            QtWidgets.QMessageBox.critical(self, 'Error', 'Error: No meshes or nodes selected.')
        path = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save File",
            "",
            "PLY File (*.ply)",
        )
        if path[0]:
            ret = self.vtk.save_ply(path=path[0])
            if ret != 1:
                QtWidgets.QMessageBox.critical(self, 'Error', 'Error: Failed to save PLY file.')

    def select_menu_temp(self, point_id, shape):
        self.vtk.change_mesh(point_id, shape)

    def open_context_menu(self, point):
        point_id, num = self.vtk.get_number_context_menu()
        if num == 0:
            return
        self.contextMenu.clear()
        for i in range(num):
            action_menu = "Menu " + str(i)
            action = QtGui.QAction(action_menu, self.contextMenu)
            action.triggered.connect(lambda chk, pt=point_id, shape=i: self.select_menu_temp(pt, shape))
            self.contextMenu.addAction(action)
        self.contextMenu.exec(self.ui.vtkWidget.mapToGlobal(point))


def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainView()
    main_window.show()
    # main_window.iren.Initialize()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

