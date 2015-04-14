// Accept a value from a file input based on a required mimetype
jQuery.validator.addMethod('filesizeCheck', function(value, element, param) {
    // param = size (en bytes) 
    // element = element to validate (<input>)
    // value = value of the element (file name)
    var result = this.optional(element) || (element.files[0].size <= param)
    if(false == result){
        alert('允许最大文件大小为:' + param + "字节.")
    }
    return result
}, "文件大小超出限制.");

// Older "accept" file extension method. Old docs: http://docs.jquery.com/Plugins/Validation/Methods/accept
jQuery.validator.addMethod("extension", function(value, element, param) {
    param = typeof param === "string" ? param.replace(/,/g, "|") : "png|jpe?g|gif";
    var result = (this.optional(element) || value.match(new RegExp(".(" + param + ")$", "i")));
    if( null == result){
        alert('仅允许上传:' + param + '格式文件.')
    }
    return result
}, $.validator.format("请上传正确格式的文件."));