tinymce.init({
    selector: 'textarea[name="content"]',
    height: 400,
    menubar: false,
    plugins: 'advlist autolink lists link image charmap preview anchor searchreplace visualblocks code fullscreen insertdatetime media table help wordcount',
    toolbar: 'undo redo | blocks | bold italic forecolor | alignleft aligncenter alignright | bullist numlist | removeformat | help',
    content_style: 'body { font-family:Poppins,sans-serif; font-size:14px }'
  });