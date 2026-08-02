#import <AppKit/AppKit.h>
#import <AVFoundation/AVFoundation.h>
#import <CoreVideo/CoreVideo.h>
#import <Foundation/Foundation.h>

static CVPixelBufferRef PixelBufferFromImage(NSImage *image, NSDictionary *attributes) {
    const size_t width = 1280, height = 720;
    CVPixelBufferRef buffer = NULL;
    CVReturn result = CVPixelBufferCreate(kCFAllocatorDefault, width, height,
                                           kCVPixelFormatType_32BGRA,
                                           (__bridge CFDictionaryRef)attributes,
                                           &buffer);
    if (result != kCVReturnSuccess || !buffer) return NULL;
    CVPixelBufferLockBaseAddress(buffer, 0);
    void *base = CVPixelBufferGetBaseAddress(buffer);
    size_t bytesPerRow = CVPixelBufferGetBytesPerRow(buffer);
    CGColorSpaceRef colorSpace = CGColorSpaceCreateDeviceRGB();
    CGContextRef context = CGBitmapContextCreate(base, width, height, 8,
                                                  bytesPerRow, colorSpace,
                                                  kCGImageAlphaPremultipliedFirst |
                                                  kCGBitmapByteOrder32Little);
    CGColorSpaceRelease(colorSpace);
    if (!context) {
        CVPixelBufferUnlockBaseAddress(buffer, 0);
        CVPixelBufferRelease(buffer);
        return NULL;
    }
    CGContextSetRGBFillColor(context, 0, 0, 0, 1);
    CGContextFillRect(context, CGRectMake(0, 0, width, height));
    CGImageRef cgImage = [image CGImageForProposedRect:NULL context:nil hints:nil];
    CGContextDrawImage(context, CGRectMake(0, 0, width, height), cgImage);
    CGContextRelease(context);
    CVPixelBufferUnlockBaseAddress(buffer, 0);
    return buffer;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 4) {
            fprintf(stderr, "usage: encode_video <frames-dir> <timeline.json> <output.mp4>\n");
            return 2;
        }
        NSString *framesDir = [NSString stringWithUTF8String:argv[1]];
        NSData *timelineData = [NSData dataWithContentsOfFile:[NSString stringWithUTF8String:argv[2]]];
        NSError *error = nil;
        NSArray *timeline = [NSJSONSerialization JSONObjectWithData:timelineData options:0 error:&error];
        if (!timeline || error) {
            fprintf(stderr, "timeline error: %s\n", error.localizedDescription.UTF8String);
            return 1;
        }
        NSURL *outputURL = [NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[3]]];
        [[NSFileManager defaultManager] removeItemAtURL:outputURL error:nil];

        AVAssetWriter *writer = [[AVAssetWriter alloc] initWithURL:outputURL fileType:AVFileTypeMPEG4 error:&error];
        NSDictionary *compression = @{
            AVVideoAverageBitRateKey: @2000000,
            AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
        };
        NSDictionary *settings = @{
            AVVideoCodecKey: AVVideoCodecTypeH264,
            AVVideoWidthKey: @1280,
            AVVideoHeightKey: @720,
            AVVideoCompressionPropertiesKey: compression,
        };
        AVAssetWriterInput *input = [AVAssetWriterInput assetWriterInputWithMediaType:AVMediaTypeVideo outputSettings:settings];
        input.expectsMediaDataInRealTime = NO;
        NSDictionary *attributes = @{
            (NSString *)kCVPixelBufferPixelFormatTypeKey: @(kCVPixelFormatType_32BGRA),
            (NSString *)kCVPixelBufferWidthKey: @1280,
            (NSString *)kCVPixelBufferHeightKey: @720,
        };
        AVAssetWriterInputPixelBufferAdaptor *adaptor =
            [AVAssetWriterInputPixelBufferAdaptor assetWriterInputPixelBufferAdaptorWithAssetWriterInput:input
                                                                              sourcePixelBufferAttributes:attributes];
        if (![writer canAddInput:input]) {
            fprintf(stderr, "cannot add video input\n");
            return 1;
        }
        [writer addInput:input];
        if (![writer startWriting]) {
            fprintf(stderr, "writer error: %s\n", writer.error.localizedDescription.UTF8String);
            return 1;
        }
        [writer startSessionAtSourceTime:kCMTimeZero];

        const int32_t fps = 10;
        int64_t frame = 0;
        for (NSDictionary *slide in timeline) {
            NSString *path = [framesDir stringByAppendingPathComponent:slide[@"file"]];
            NSImage *image = [[NSImage alloc] initWithContentsOfFile:path];
            if (!image) {
                fprintf(stderr, "cannot open %s\n", path.UTF8String);
                return 1;
            }
            CVPixelBufferRef buffer = PixelBufferFromImage(image, attributes);
            if (!buffer) {
                fprintf(stderr, "cannot create frame buffer\n");
                return 1;
            }
            NSInteger count = slide[@"frames"]
                ? [slide[@"frames"] integerValue]
                : [slide[@"duration"] integerValue] * fps;
            for (NSInteger i = 0; i < count; i++) {
                while (!input.readyForMoreMediaData) [NSThread sleepForTimeInterval:0.005];
                CMTime time = CMTimeMake(frame, fps);
                if (![adaptor appendPixelBuffer:buffer withPresentationTime:time]) {
                    fprintf(stderr, "append error: %s\n", writer.error.localizedDescription.UTF8String);
                    CVPixelBufferRelease(buffer);
                    return 1;
                }
                frame++;
            }
            CVPixelBufferRelease(buffer);
        }
        [input markAsFinished];
        dispatch_semaphore_t done = dispatch_semaphore_create(0);
        [writer finishWritingWithCompletionHandler:^{ dispatch_semaphore_signal(done); }];
        dispatch_semaphore_wait(done, DISPATCH_TIME_FOREVER);
        if (writer.status != AVAssetWriterStatusCompleted) {
            fprintf(stderr, "finish error: %s\n", writer.error.localizedDescription.UTF8String);
            return 1;
        }
        printf("Created %s — %.1f seconds\n", outputURL.path.UTF8String, (double)frame / fps);
    }
    return 0;
}
