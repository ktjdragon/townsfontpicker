#入力されたコードが適切かどうかを判断するための関数
#FONT1ならJIS X0208(94区まで)、半角フォントならJIS X0201のみ(0～ff)、
#FONT2ならX0201、X0208双方OK、FontCityも同様、ただし255区まで拡張
def ValidateCommand(command, filetype):
  import re
  
  match0201 = re.match('^[0-9a-fA-F]{1,2}$', command)
  match0208 = re.match('^([0-9]{1,3}),([0-9]{1,2})$', command)
  
  if match0201 is not None:
    if filetype=='FONT1':
      ret = ('This font set does not support JIS X0201. ', None, None)
    else:
      ret = (None, 0, int(command, 16))
  elif match0208 is not None:
    block = int(match0208[1])
    point = int(match0208[2])
    if filetype=='hankaku':
      ret = ('This font set does not support JIS X0208', None, None)
    elif filetype=='FONT1' or filetype=='FONT2':
      if block > 94 or block==0:
        ret = ('block# must be between 1 and 94', None, None)
      elif point > 94 or point==0:
        ret = ('point# must be between 1 and 94', None, None)
      else:
        ret = (None, block, point)
    else:
      if block > 255 or block==0:
        ret = ('block# must be between 1 and 255', None, None)
      elif point > 94 or point==0:
        ret = ('point# must be between 1 and 94', None, None)
      else:
        ret = (None, block, point)
  else:
    ret = ('Invalid Command', None, None)
  return ret
  

#8bitのデータからテキストを得るルーチン(0->-, 1->X)
def bin2txt(dat):
  linetxt = ""
  datint = int.from_bytes(dat)
  for i in range(8):
    if datint & 128 == 128:
      linetxt += "X"
    else:
      linetxt += "-"
    datint = datint << 1
  return linetxt

#圧縮フォントデータの解凍
#帰り値は解凍後のbytes x lines個の8ビット整数のリスト
def decompressFontData(fontDataCompressed, bytes, lines):
  ret = []
  
  bytesOfHeaderPerCol = lines // 8 #1列当たりのヘッダのバイト数
  if lines % 8 != 0:
    bytesOfHeaderPerCol += 1
  
  DataAddr = bytesOfHeaderPerCol * bytes #フォントデータ本体の位置
  for i in range(bytes):
    prevData = b'\00'
    for j in range(bytesOfHeaderPerCol):
      header = int.from_bytes(fontDataCompressed[i * bytesOfHeaderPerCol + j])
      for k in range(8):
        if header & 128 == 128:
          prevData = fontDataCompressed[DataAddr]
          DataAddr += 1
        ret.append(prevData)
        header = header << 1
  return ret
  
#FontCityの非圧縮データ列からテキスト列を取得
def fcProcess(data, bytes, lines, width):
  ret = []
  for i in range(lines):
    linedata = ""
    for j in range(bytes):
      linedata += bin2txt(data[j * lines + i])
    ret.append(linedata[0:width])
    
  return ret
  
from sys import argv

#引数の取り出し
if len(argv)==1:
  print("フォントファイルが指定されていません")
  exit()

filename = argv[1]

try:
  with open(filename, mode="rb") as f:
    compress = False #FontCityの圧縮フラグ
    #ファイルタイプの取得
    byte5 = f.read(5) #先頭5バイトの取得
    if byte5==b'FONT1':
      start_msg = ''
      filetype = 'FONT1'
      f.seek(11)
      lines = int.from_bytes(f.read(1)) #垂直方向サイズ
      bytes = lines // 8 #水平方向バイト数
      if lines % 8 != 0:
        bytes += 1
      start_msg += "File Type: FNT FONT1\n"
      start_msg += "File Name: " + filename + "\n"
      start_msg += "Font Size: " + str(lines) + "dots\n"
      start_msg += "JIS X0208 blocks 1 - 94 are available.\n"
    elif byte5==b'FONT2':
      start_msg = ''
      filetype = 'FONT2'
      f.seek(11)
      lines = int.from_bytes(f.read(1)) #垂直方向サイズ
      bytes = lines // 8 #水平方向バイト数(全角)
      if lines % 8 != 0:
        bytes += 1
      width_hw = lines // 2 #半角フォントの水平方向ドット数
      bytes_hw = width_hw // 8 #水平方向バイト数(半角)
      if (lines // 2) % 8 != 0:
        bytes_hw += 1
      start_msg += "File Type: FNT FONT2\n"
      start_msg += "File Name: " + filename + "\n"
      start_msg += "Font Size: " + str(lines) + "dots\n"
      start_msg += "JIS X0201 block and JIS X0208 blocks 1 - 94 are available.\n"
    elif byte5[0:3]==b'\r\n\t':
      start_msg = ''
      #最初の3バイトがCR,LF,タブの場合はFontCityとみなす
      filetype = 'FontCity'
      f.seek(int('31C', 16))
      lines = int.from_bytes(f.read(1)) #垂直方向サイズ
      width = lines #水平方向サイズ
      bytes = width // 8 #水平方向バイト数(全角)
      if width % 8 != 0:
        bytes += 1
      width_hw = width // 2 #水平方向サイズ(半角)
      bytes_hw = width_hw // 8 #水平方向バイト数(半角)
      if width_hw % 8 != 0:
        bytes_hw += 1
      start_msg += "File Type: FontCity\n"
      start_msg += "File Name: " + filename + "\n"
      f.seek(int('340', 16))
      if f.read(1)==b'\xff':
        compress = True
      f.seek(int('200', 16))
      fontname_b = b''
      while True:
        bytedata = f.read(1)
        if bytedata==b'\x00':
          break
        else:
          fontname_b += bytedata
      fontname = fontname_b.decode("shift_jis")
      start_msg += "Font Name: " + fontname + "\n"
      start_msg += "Font Size: " + str(lines) + "dots\n"
      
      #利用可能な区を確認
      seek_address = 1024
      f.seek(seek_address)
      available_blocks = []
      for i in range(256):
        address = f.read(4)
        if address != b'\x00\x00\x00\x00':
          available_blocks.append(i)
      for i in range(len(available_blocks)):
        if i==0:
          if available_blocks[0]==0:
            #最初のブロックがJIS X0201の場合
            start_msg += "JIS X0201 block"
          else:
            #最初のブロックがJIS X0208の場合
            start_msg += "JIS X0208 block(s) " + str(available_blocks[0])
        elif i==1:
          if available_blocks[0]==0:
            #最初のブロックがJIS X0201かつ2番目のブロックがある場合
            start_msg += ", JIS X0208 block(s) " + str(available_blocks[1])
          elif available_blocks[0] + 1 < available_blocks[1]:
            #最初のブロックがX0208かつ2番目のブロックよりも2以上小さい場合
            start_msg += ", " + str(available_blocks[1])
        elif i==2 and available_blocks[0]==0 and available_blocks[1] + 1 < available_blocks[2]:
          #最初のブロックがJIS X0201かつ3番目のブロックが2番目のブロックよりも2以上大きい場合
          start_msg += ", " + str(available_blocks[2])
        elif available_blocks[i]>available_blocks[i-1]+1:
          #上記のパターン以外で前ブロックよりも2以上大きい場合
          if available_blocks[i-1]>available_blocks[i-2]+1:
            #かつ前ブロックが前々ブロックよりも2以上大きい場合
            start_msg += ", " + str(available_blocks[i])
          else:
            #そうでない場合(前ブロックが前々ブロックよりも1大きい場合)
            start_msg += " - " + str(available_blocks[i-1]) + ", " + str(available_blocks[i])
      start_msg += " are available.\n"
    else:
      #上記のいずれにも該当しない場合は半角フォントとみなす
      start_msg = ''
      filetype = 'hankaku'
      lines = 24
      bytes = 3
      width_hw = 12
      start_msg += "File Type: FNT halfwidth or halfwidth-halfheight\n"
      start_msg += "File Name: " + filename + "\n"
      start_msg += "Font Size: " + str(lines) + "dots\n"
      start_msg += "JIS X0201 block is available.\n"
    
    print(start_msg)
    
    usage_msg = "JIS X0201 code: 8bit hex\n"
    usage_msg += "JIS X0208 code: block,point\n"
    usage_msg += "i: display file info\n"
    usage_msg += "u: display usage\n"
    usage_msg += "enter: display next letter\n"
    usage_msg += "q: quit\n"
    
    print(usage_msg)
    
    #デフォルトのコードを設定
    if filetype=='hankaku' or 'FONT2':
      code = [0, 0] #半角又はFONT2はJIS X0201 0x00
    elif filetype=='FONT1':
      code = [1, 1] #FONT1はJIS X0208 区画1の最初の文字
    else: #FontCityは最初に検出した区画の最初の文字にする
      f.seek(1024)
      for i in range(256):
        if f.read(4)!=b'\x00\x00\x00\x00':
          break
      if i==0:
        code = [0, -1] #半角文字がある場合はJIS X0201 0x00
      else:
        code = [i, 0] #ない場合は 最初に検出した区画の最初の文字

    #フォント表示ループ
    while True:
    
    
      command = input("Input code or command>")
      
      if command=="q":
        break
      elif command=="i":
        print(start_msg)
      elif command=="u":
        print(usage_msg)
      else:
        if command=='':
          #何も入力せずにエンターを押した場合はデフォルトのコードに1を加算する
          if code[0]==0:
            if code[1]==255:
              VC_result = ('It reaches end of JIS X0201 code', None, None)
            else:
              VC_result = (None, code[0], code[1]+1)
          elif code[1]==94:
            VC_result = ('It reaches end of JIS X0208 block ' + str(code[0]), None, None)
          else:
            VC_result = (None, code[0], code[1]+1)
        else:
          VC_result = ValidateCommand(command, filetype)
        
        if filetype=='FontCity' and VC_result[0] is None:
          #FontCityの場合はその区にフォントがあるかチェックする
          f.seek(1024 + 4 * VC_result[1])
          if f.read(4)==b'\x00\x00\x00\x00':
            if VC_result[1]==0:
              VC_result = ("This font set does not support JIS X0201", None, None)
            else:
              VC_result = ("This font set does not support JIS X0208 block " + str(VC_result[1]), None, None)
        if VC_result[0] is not None:
          print(VC_result[0])
        else:
          #コードの指定
          code = [VC_result[1], VC_result[2]]
          
          #データの取得と表示
          fontdata = []
          if filetype=="FONT1":
            offset = 16 + ((code[0] - 1) * 94 + code[1] - 1) * (bytes * lines + 2) + 2
            f.seek(offset)
            for line in range(lines):
              linedata = ""
              for byte in range(bytes):
                linedata += bin2txt(f.read(1))
              #(不必要だと思うけど)余計なデータのトリミング
              linedata = linedata[0:lines]
              fontdata.append(linedata)
            
          elif filetype=="FONT2":
            if code[0]==0: #半角の場合
              offset = 16 + code[1] * bytes_hw * lines
              f.seek(offset)
              for line in range(lines):
                linedata = ""
                for byte in range(bytes_hw):
                  linedata += bin2txt(f.read(1))
                linedata = linedata[0:width_hw]
                fontdata.append(linedata)
            else: #全角の場合
              offset = 16 + bytes_hw * lines * 256 + ((code[0] - 1) * 94 + code[1] - 1) * bytes * lines
              f.seek(offset)
              for line in range(lines):
                linedata = ""
                for byte in range(bytes):
                  linedata += bin2txt(f.read(1))
                linedata = linedata[0:lines]
                fontdata.append(linedata)
          elif filetype=="hankaku":
            offset = (bytes * lines + 2) * code[1] + 2
            f.seek(offset)
            for line in range(lines):
              linedata = ""
              for byte in range(bytes):
                linedata += bin2txt(f.read(1))
              linedata = linedata[0:width_hw]
              fontdata.append(linedata)
          elif compress: #FontCity圧縮
            offset = int('400', 16) + code[0] * 4
            f.seek(offset)
            #区画の先頭のアドレスを取得
            offset = int.from_bytes(f.read(4), 'little')
            
            #文字のアドレスを取得
            if code[0]==0:
              f.seek(offset + 6 * code[1])
            else: 
              f.seek(offset + 6 * (code[1] -1))
            offset = int.from_bytes(f.read(4), 'little')
            bytesOfChar = int.from_bytes(f.read(2), 'little') #文字データのバイト数
            
            #データの取得
            f.seek(offset)
            fontDataCompressed = []
            for i in range(bytesOfChar):
              fontDataCompressed.append(f.read(1))
            
            #圧縮データの解凍とテキストデータ化
            if code[0]==0:
              fontdata = fcProcess(decompressFontData(fontDataCompressed, bytes_hw, lines), bytes_hw, lines, width_hw)
            else:
              fontdata = fcProcess(decompressFontData(fontDataCompressed, bytes, lines), bytes, lines, lines)
              
          else: #FontCity非圧縮
            offset = int('400', 16) + code[0] * 4
            f.seek(offset)
            #区画の先頭のアドレスを取得
            offset = int.from_bytes(f.read(4), 'little')
            #フォントデータの取得
            dataList = []
            if code[0]==0:
              offset += bytes_hw * lines * code[1]
              print(hex(offset))
              f.seek(offset)
              for i in range(bytes_hw * lines):
                dataList.append(f.read(1))
              fontdata = fcProcess(dataList, bytes_hw, lines, width_hw)
            else:
              offset += bytes * lines * (code[1] -1)
              f.seek(offset)
              for i in range(bytes * lines):
                dataList.append(f.read(1))
              fontdata = fcProcess(dataList, bytes, lines, lines)
            
          #フォントデータの表示
          if code[0]==0:
            if code[1]<16:
              hexcode = "0" + hex(code[1])[2:]
            else:
              hexcode = hex(code[1])[2:]
            print("JIS X0201 code " + hexcode)
          else:
            print("JIS X0208 block " + str(code[0]) + ", point " + str(code[1]))
          for dat in fontdata:
            print(dat)
    

    
    
except FileNotFoundError:
  print("フォントファイルが見つかりません")

