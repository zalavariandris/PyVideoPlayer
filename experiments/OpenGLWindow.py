from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtOpenGLWidgets import *
from PySide6.QtOpenGL import *
from PySide6.support import VoidPtr
import numpy as np

from OpenGL.GL import *

from pathlib import Path

# Under the skin: 1:29 motoros jelenet

class Window(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        # opengl data related
        self.context = QOpenGLContext()
        fmt =  QSurfaceFormat.defaultFormat()
        fmt.setVersion(3, 3)
        self.context.setFormat(fmt)
        self.vao = QOpenGLVertexArrayObject()
        self.vbo = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        self.vbo_uv = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        self.program = QOpenGLShaderProgram()

        self.indices = np.array(
            [0,1,3,
            1,2,3],
            dtype=ctypes.c_uint
        )

        self.vertexData = np.array([
            # corners of the rectangle
            0.5,  0.5,  0.0,  # top right
            0.5,  -0.5, 0.0,  # bottom right
            -0.5, -0.5, 0.0,  # bottom left
            -0.5, 0.5,  0.0,  # top left
        ], dtype=ctypes.c_float)

        self.uvData = np.array([
            1, 1, # top right
            1, 0,  # bottom right
            0, 0,  # bottom left
            0, 1  # top left
        ], dtype=ctypes.c_float)
        # triangle color
        self.triangleColor = QVector4D(0.5, 0.5, 0.0, 0.0)

        image_path = Path("../tests/resources/MASA_sequence/MASA_sequence_00197.jpg")
        assert image_path.exists()
        self.image = QImage(str(image_path)).mirrored()
        self.texture = None

    def getGLInfo(self):
        "Get opengl info"
        info = """
            OpenGL INFO
            -----------
            ES:             {}
            Vendor:         {}
            Renderer:       {}
            OpenGL Version: {}
            Shader Version: {}
            """.format(
            self.context.isOpenGLES(),
            glGetString(GL_VENDOR).decode('utf-8'),
            glGetString(GL_RENDERER).decode('utf-8'),
            glGetString(GL_VERSION).decode('utf-8'),
            glGetString(GL_SHADING_LANGUAGE_VERSION).decode('utf-8')
        )
        return "\n".join([line.lstrip() for line in info.split("\n")])

    def paintGL(self):
        funcs = self.context.functions()

        funcs.glClear(GL_COLOR_BUFFER_BIT)

        vaoBinder = QOpenGLVertexArrayObject.Binder(self.vao)
        self.program.bind()
        self.texture.bind()
        funcs.glDrawElements(GL_TRIANGLES, self.indices.size, GL_UNSIGNED_INT, self.indices.tobytes())
        self.program.release()
        vaoBinder = None # we can unbind the vao since again the frame is drawn

    def resizeGL(self, width: int, height: int):
        funcs = self.context.functions()
        funcs.glViewport(0,0,width, height)

    def cleanUpGL(self):
        self.context.makeCurrent()
        self.vbo.destroy()
        del self.program
        self.program = None
        self.doneCurrent()

    def initializeGL(self):
        print("initialize gl")
        print(self.getGLInfo())

        self.context.create()

        self.context.aboutToBeDestroyed.connect(lambda: self.cleanUpGL())

        funcs = self.context.functions()
        funcs.initializeOpenGLFunctions()
        funcs.glClearColor(1, 1, 1, 1)

        # read and compile shaders
        vertex_path = Path("./triangle.vert")
        assert vertex_path.exists()
        vertex_source = vertex_path.read_text()
        vshader = QOpenGLShader(QOpenGLShader.Vertex)
        vshader_compiled = vshader.compileSourceCode(vertex_source)
        assert vshader_compiled

        fragment_path = Path("./triangle.frag")
        assert fragment_path.exists()
        fragment_source = fragment_path.read_text()
        fshader = QOpenGLShader(QOpenGLShader.Fragment)
        fshader_compiled = fshader.compileSourceCode(fragment_source)
        assert fshader_compiled


        # create shader program
        self.program = QOpenGLShaderProgram(self.context)
        self.program.addShader(vshader)
        self.program.addShader(fshader)

        self.program.bindAttributeLocation("position", 0)
        self.program.bindAttributeLocation("uv", 1)

        # link shader program
        isLinked = self.program.link()
        print("shader program is linked: ", isLinked)
        # if the program is not linked we won't have any output so
        # it is important to check for it

        # bind the program == activate the program
        self.program.bind()

        # specify uniform value
        colorLoc = self.program.uniformLocation("color") 
        # notice the correspondance of the
        # name color in fragment shader
        # we also obtain the uniform location in order to 
        # set value to it
        self.program.setUniformValue(colorLoc, self.triangleColor)

        # vao
        isVao = self.vao.create()
        vaoBinder = QOpenGLVertexArrayObject.Binder(self.vao)

        # vbo
        isVbo = self.vbo.create()
        isBound = self.vbo.bind()

        # check if vao and vbo are created
        print('vao created: ', isVao)
        print('vbo created: ', isVbo)

        floatSize = ctypes.sizeof(ctypes.c_float)

        # allocate space on buffer
        self.vbo.allocate(self.vertexData.tobytes(),  # the actual content of the data
                          floatSize * self.vertexData.size  # the size of the data
                         )

        # self.vbo_uv.allocate(self.uvData.tobytes(), floatSize * self.uvData.size)

        funcs.glEnableVertexAttribArray(0)  
        # 0 represent the location of aPos
        # we know this number because it is us who bind it to that location above
        nullptr = VoidPtr(0)  # no idea what we do with this thing.
        funcs.glVertexAttribPointer(0,  # the location of aPos attribute
                                    3,  # 3 for vec3
                                    int(GL_FLOAT),  # type of value in the coordinates
                                    # notice that we use a flag from opengl
                                    int(GL_FALSE),  # should we normalize the coordinates
                                    # or not
                                    3 * floatSize, # stride. That is when does the next vertice
                                    # start in the array
                                    nullptr  # offset. From where the coordinates starts
                                    # in the array, since we only have vertex coordinates 
                                    # in the array, we start from 0
                                   )

        self.vbo.release()

        self.vbo_uv.create()
        self.vbo_uv.bind()
        self.vbo.allocate(self.uvData.tobytes(),  # the actual content of the data
                          floatSize * self.vertexData.size  # the size of the data
                         )
        funcs.glEnableVertexAttribArray(1)
        funcs.glVertexAttribPointer(1, 2, int(GL_FLOAT), int(GL_FALSE), 2*floatSize, nullptr)

        
        self.vbo_uv.release()
        self.program.release()
        vaoBinder = None

        # load the texture
        self.texture = QOpenGLTexture(QOpenGLTexture.Target2D)
        assert self.texture
        self.texture.create()
        # new school
        self.texture.bind()
        self.texture.setData(self.image)
        self.texture.setMinMagFilters(QOpenGLTexture.Linear,
                                      QOpenGLTexture.Linear)
        self.texture.setWrapMode(QOpenGLTexture.DirectionS,
                                 QOpenGLTexture.Repeat)
        self.texture.setWrapMode(QOpenGLTexture.DirectionT,
                                 QOpenGLTexture.Repeat)

if __name__ == "__main__":
    app = QApplication.instance() or QApplication()
    window = Window()
    window.show()
    app.exec_()