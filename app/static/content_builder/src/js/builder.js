function create_box(special_modifier) {

    var insert_special = ""
    var title_template = ""
    var additional_body = null

    if (special_modifier == null) {
        insert_special = ""
        title_template = "Title of the box goes here..."
    }


    if (special_modifier == "obj") {
        insert_special = "<span class=\"box-icon objective\"></span> <span class=\"blue-text\">Key objective of this session: </span>",
            title_template = "type in the lesson objective here..."
    } else if (special_modifier == "file") {
        insert_special = "<div class=\"box-title\"><span class=\"box-icon file\"></span><span class=\"blue-text\">Required Resources</span></div>",
            title_template = null
        additional_body = "<button class=\"upload_file btn\">Add a file <i class=\"fa fa-folder-plus\" aria-hidden=\"true\"></i></button>"
    }

    var box = document.createElement("div");
    box.className = "boxed";
    box.innerHTML = "<div class=\"tools\"><button class=\"remove_button\"><i class=\"fa fa-trash\" aria-hidden=\"true\"></i></button><button class=\"move_button\"><i class=\"fas fa-arrows-alt-v\" aria-hidden=\"true\"></i></button></div>"

    var heading = document.createElement("div");
    heading.className = "box-heading";

    var title = document.createElement("span");
    title.className = "box-title";
    title.innerHTML = insert_special

    if (title_template != null) {
        var title_text = document.createElement("p");
        title_text.className = "title-text editable";
        title_text.innerHTML = title_template
    }

    if (additional_body != null) {
        var add_bod = document.createElement("div");
        add_bod.className = "add_file_buttons";
        add_bod.innerHTML = additional_body
    }

    var body = document.createElement("div");
    body.className = "box-body editable";
    body.innerHTML = "Content of step goes here..."

    heading.appendChild(title);
    if (title_template != null) { title.appendChild(title_text); }

    box.appendChild(heading);
    box.appendChild(body);
    if (additional_body != null) { box.appendChild(add_bod); }

    document.getElementById("viewer").appendChild(box);

    var editorColOne = new MediumEditor('.editable', {
        paste: {
            /* This example includes the default options for paste,
               if nothing is passed this is what it used */
            forcePlainText: false,
            cleanPastedHTML: false,
            cleanReplacements: [],
        },
        toolbar: {
            sticky: true,
            static: true,
            align: 'right',
            updateOnEmptySelection: true,
            buttons: ['bold', 'italic', 'underline', 'strikethrough', 'quote', 'justifyLeft', 'justifyCenter', 'superscript', 'subscript',
                'orderedlist', 'unorderedlist', 'pre', 'h1'
            ],
        },
        buttonLabels: 'fontawesome',
    });

    // List with handle
    Sortable.create(viewer, {
        handle: '.move_button',
        animation: 150,
        ghostClass: 'ghost'
    });

    //adds remove dialog to the block
    $('.remove_button').confirm({
        title: 'Confirm Deletion',
        icon: 'fa fa-warning',
        content: 'Do you want to delete this block?',
        type: 'red',
        theme: 'supervan',
        buttons: {
            confirm: {
                btnClass: 'btn-red',
                action: function () {
                    this.$target.parent().parent().remove();
                }
            },
            cancel: function () { }
        }
    });

    $('.upload_file').confirm({
        title: 'Add file URL',
        content: '' +
            '<form action="" class="fileForm">' +
            '<div class="form-group">' +
            '<label>Input name & web link to resource</label>' +
            '<input type="text" placeholder="Name" class="name form-control" required />' +
            '<input type="text" placeholder="URL" class="link form-control" required />' +
            '</div>' +
            '</form>',
            theme: 'supervan',
            buttons: {
            formSubmit: {
                text: 'Submit',
                btnClass: 'btn-blue',
                action: function () {
                    var name = this.$content.find('.name').val();
                    var link = this.$content.find('.link').val();
                    if (!name) {
                        $.alert('Provide a valid name');
                        return false;
                    }
                    if (!link) {
                        $.alert('Provide a valid link');
                        return false;
                    }


                    var file_button = document.createElement("button");
                    file_button.className = "file_link btn";
                    file_button.href = link;
                    file_button.innerHTML = name + "<i class=\"fas fa-external-link-alt left-space\"></i>";

                    console.log(this.$target.parent()[0])
                    this.$target.parent()[0].appendChild(file_button);

                }
            },
            cancel: function () {
                //close
            },
        },
        onContentReady: function () {
            // bind to events
            var jc = this;
            this.$content.find('form').on('submit', function (e) {
                // if the user submits the form by pressing enter in the field.
                e.preventDefault();
                jc.$$formSubmit.trigger('click'); // reference the button and click it
            });
        }
    });

    //template
    $("button").click(function () {
        var myClass = this.className;
        if (myClass == "remove_button") {
        }
    });
}

$("button").click(function () {
    var myClass = this.className;
    if (myClass == "create_box box_basic") { create_box(); }
    else if (myClass == "create_box box_obj") { create_box("obj"); }
    else if (myClass == "create_box box_file") { create_box("file"); }

});

create_box();
create_box("obj");
create_box("file");