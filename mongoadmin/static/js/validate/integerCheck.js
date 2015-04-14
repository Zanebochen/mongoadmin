// 整数验证
jQuery.validator.addMethod("integerCheck", function(value, element) {
    var re = new RegExp("^-?\\d+$");  
    return (Number(value) >= -2147483648 && Number(value) <= 2147483647) && value.match(re) != null;
}, "只能输入整数。");