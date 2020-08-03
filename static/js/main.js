/* global $ */
"use strict";

$(document).ready(function () {
    
    /**
     * CKEditor initialisieren
     */
    $.each(document.getElementsByClassName('texteditor'), function (index, object) {
        ClassicEditor
            .create(object, {
                toolbar: ["heading", "|", "bold", "italic", "link", "bulletedList", "numberedList", "blockQuote"],
                heading: {
                    options: [
                        {model: "paragraph", title: "Paragraph", class: "ck-heading_paragraph"},
                        {model: "heading1", view: "h1", title: "Heading 1", class: "ck-heading_heading1"},
                        {model: "heading2", view: "h2", title: "Heading 2", class: "ck-heading_heading2"}
                    ]
                }
            })
            .catch(error => {
                console.error(error);
            });
    });


    /**
     * Input Type Checkbox manipulieren -> WT Forms sendet ein "y" statt 1
     */
    if ($("input[type=checkbox]").val() == "y") {
        $("input[type=checkbox]").val(1)
    }
    $("input[type=checkbox]").bind("click touch", function () {
        if ($(this).prop("checked") === true) {
            $(this).val(1)
        } else {
            $(this).val(0)
        }
    });


    $(".fileupload").each(function () {
        let infoString = "";

        if ($(this).attr("data-max-size")) {
            infoString += $(this).attr("data-max-size");
        }

        if ($(this).attr("data-extensions")) {

            if (infoString !== "") {
                infoString += " ";
            }

            infoString += " ( " + $(this).attr("data-extensions") + " ) ";
        }

        $(this).parent(".fileupload-container").append("<span class='info' style='display:block;'>" + infoString.toString() + "</span>");
    });

    $(".fileupload").hide();

    $(".fileupload-container").dropzone({
        url: "/backend/ajax/image_upload",
        method: "POST",
        widthCredentials: true, // Session Cookie mitschicken
        addRemoveLinks: true,
        //acceptedFiles: ["image/jpg", "image/png", "image/gif", "image/svg+xml"],
        maxFiles: 1, // 1 Datei
        maxFilesize: 30, // 30 MB
        params: {
            "type": $("#type").val(),
            "module": $("#module").val(),
            "id": $("#id").val()
        },
        init: function () {
            this.on("sending", function (file, xhr, formData) {
                // image format in init funktion übergeben ist sonst undefined ?
                formData.append("image_format", $(this.element).children('.image-format').val());
                formData.append("max_files", $(this.element).children('.max_files').val());
                formData.append("max_size", $(this.element).children('.max_size').val());
            });
        },
        error: function (error) {
            $(this).children(".type");
            $(".dz-success-mark").hide();
            $(".dz-error-mark").show();
        },
        success: function () {
            $(".dz-success-mark").show();
            $(".dz-error-mark").hide();
        }
    });

    $('#tab-meta, #tab-ctrl').hide();

    $('.nav-tabs .nav-link').bind("click touch", function () {
        let tab_id = "#tab-" + $(this).attr('data-tab-id');
        $('.tab').hide();
        $(tab_id).show();
    });

});