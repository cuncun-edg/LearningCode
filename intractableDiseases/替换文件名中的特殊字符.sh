# ls -b 显示文件名的详细信息，包括隐藏的特殊字符
# 使用 tr 命令删除所有不可见的特殊字符

for file in *; do
  newfile=$(echo "$file" | tr -d '\351\222')
  mv "$file" "$newfile"
done

