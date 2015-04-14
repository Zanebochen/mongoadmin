// 手机号码验证
jQuery.validator.addMethod("isPhone", function(value, element) { 
    var length = value.length; 
    var mobile = /^(((13[0-9]{1})|(15[0-9]{1}))+\d{8})$/ 
    return this.optional(element) || (length == 11 && mobile.test(value)); 
}, "手机号码格式错误");
