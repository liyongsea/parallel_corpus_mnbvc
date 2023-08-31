' 使用方法：新建空白word，添加vba宏，将下面的文件夹路径改为实际的路径，然后运行，他会自动递归的转

Sub ConvertAllDocsToDocx()
    Dim FolderPath As String
    
    ' 设置文件夹路径
    FolderPath = "C:\YourFolderPath\" ' 替换为实际的文件夹路径
    
    ' 调用递归处理的子过程
    ConvertDocsToDocxRecursive FolderPath
    
    MsgBox "转换完成！"
End Sub

Sub ConvertDocsToDocxRecursive(FolderPath As String)
    Dim FileName As String
    Dim SubFolder As Object
    Dim SubFolderItems As Object
    
    ' 获取文件夹中的所有文件
    FileName = Dir(FolderPath & "\*.*")
    
    ' 循环处理文件夹中的文件
    Do While FileName <> ""
        ' 判断文件是否为doc文件
        If LCase(Right(FileName, 4)) = ".doc" Then
            ' 打开并另存为docx格式
            Documents.Open FileName:=FolderPath & "\" & FileName
            ' 禁用保存时的提示框
            Application.DisplayAlerts = False
            ActiveDocument.SaveAs2 FileName:=FolderPath & "\" & Left(FileName, Len(FileName) - 4) & ".docx", FileFormat:=wdFormatXMLDocument
            ActiveDocument.Close
            ' 启用保存时的提示框
            Application.DisplayAlerts = True
            
            ' 删除原来的doc文件
            Kill FolderPath & "\" & FileName
        End If
        
        ' 获取下一个文件
        FileName = Dir
    Loop
    
    ' 递归处理子文件夹
    Set SubFolderItems = CreateObject("Scripting.FileSystemObject").GetFolder(FolderPath).SubFolders
    For Each SubFolder In SubFolderItems
        ConvertDocsToDocxRecursive SubFolder.Path
    Next SubFolder
End Sub