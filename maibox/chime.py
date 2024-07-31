import ctypes
import os.path
import platform


class CommSafeHandle:
    def __init__(self, handle):
        self.handle = handle

    def is_invalid(self):
        return self.handle is None or self.handle == 0

class GetUserData:
    def __init__(self, strGameID, strChipID, strCommonKey, strQRData):
        if platform.system() == 'Windows':
            self.lib = ctypes.cdll.LoadLibrary(os.path.join(os.path.dirname(__file__), './bin/chimelib_dll.dll'))
            self.instance = self.create(strGameID, strChipID, strCommonKey, strQRData)
        else:
            self.instance = None

    def create(self, strGameID, strChipID, strCommonKey, strQRData):
        if platform.system() != 'Windows':
            return None
        create_func = self.lib.CCommGetUserData_Create
        create_func.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_wchar_p]
        create_func.restype = ctypes.c_void_p
        handle = create_func(strGameID, strChipID, strCommonKey, strQRData)
        return CommSafeHandle(handle)

    def destroy(self):
        if not self.instance:
            return
        destroy_func = self.lib.CCommGetUserData_Destroy
        destroy_func.argtypes = [ctypes.c_void_p]
        destroy_func(self.instance.handle)

    def get_error_id(self):
        if not self.instance:
            return 50
        get_error_id_func = self.lib.CCommGetUserData_getErrorID
        get_error_id_func.argtypes = [ctypes.c_void_p]
        get_error_id_func.restype = ctypes.c_int
        return get_error_id_func(self.instance.handle)

    def is_end(self):
        if not self.instance:
            return True
        is_end_func = self.lib.CCommGetUserData_isEnd
        is_end_func.argtypes = [ctypes.c_void_p]
        is_end_func.restype = ctypes.c_bool
        return is_end_func(self.instance.handle)

    def get_user_id(self):
        if not self.instance:
            return 0
        get_user_id_func = self.lib.CCommGetUserData_getUserID
        get_user_id_func.argtypes = [ctypes.c_void_p]
        get_user_id_func.restype = ctypes.c_uint
        return get_user_id_func(self.instance.handle)

    def execute(self):
        if not self.instance:
            return
        execute_func = self.lib.CCommGetUserData_execute
        execute_func.argtypes = [ctypes.c_void_p]
        execute_func(self.instance.handle)
